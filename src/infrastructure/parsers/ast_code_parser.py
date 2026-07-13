import ast
from typing import List, Optional
from src.interfaces.gateways.code_parser import CodeParserGateway
from src.domain.models import CodeChunk
from src.domain.exceptions import ParserError

def get_decorator_name(decorator: ast.AST) -> str:
    """Helper to extract the full name of a decorator (e.g. app.router.get)."""
    if isinstance(decorator, ast.Name):
        return decorator.id
    elif isinstance(decorator, ast.Attribute):
        parts = []
        curr = decorator
        while isinstance(curr, ast.Attribute):
            parts.append(curr.attr)
            curr = curr.value
        if isinstance(curr, ast.Name):
            parts.append(curr.id)
        return ".".join(reversed(parts))
    elif isinstance(decorator, ast.Call):
        return get_decorator_name(decorator.func)
    return ""

def classify_function(node: ast.AST) -> str:
    """Classifies function nodes into function, api_endpoint, or cli_command."""
    for dec in node.decorator_list:
        dec_name = get_decorator_name(dec)
        # Check API Endpoint criteria
        if any(suffix in dec_name for suffix in [".get", ".post", ".put", ".delete", ".patch", ".route", "route"]):
            return "api_endpoint"
        # Check CLI Command criteria
        if any(keyword in dec_name for keyword in ["click.command", "click.option", "click.argument", "command", "option"]):
            return "cli_command"
    return "function"

def classify_class(node: ast.ClassDef) -> str:
    """Classifies class nodes into class or configuration_schema."""
    # 1. Check bases (inheritance)
    for base in node.bases:
        base_name = ast.unparse(base)
        if any(pydantic_base in base_name for pydantic_base in ["BaseModel", "BaseSettings"]):
            return "configuration_schema"
            
    # 2. Check decorators
    for dec in node.decorator_list:
        dec_name = get_decorator_name(dec)
        if "dataclass" in dec_name:
            return "configuration_schema"
            
    # 3. Check name suffix/heuristics
    if any(suffix in node.name.lower() for suffix in ["settings", "config"]):
        return "configuration_schema"
        
    return "class"

def get_function_signature(node: ast.AST) -> str:
    """Reconstructs the function signature using ast.unparse."""
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return ""
    
    args_list = []
    
    # Track positional arguments and their defaults
    posonly = getattr(node.args, "posonlyargs", [])
    all_pos = [(arg, True) for arg in posonly] + [(arg, False) for arg in node.args.args]
    defaults = getattr(node.args, "defaults", [])
    defaults_offset = len(all_pos) - len(defaults)
    
    # Positional-only args
    posonly_formatted = []
    for idx, (arg, is_pos) in enumerate(all_pos):
        if not is_pos:
            continue
        ann = f": {ast.unparse(arg.annotation)}" if arg.annotation else ""
        default_val = ""
        if idx >= defaults_offset:
            default_val = f" = {ast.unparse(defaults[idx - defaults_offset])}"
        posonly_formatted.append(f"{arg.arg}{ann}{default_val}")
    if posonly_formatted:
        args_list.extend(posonly_formatted)
        args_list.append("/")
        
    # Standard args (positional or keyword)
    for idx, (arg, is_pos) in enumerate(all_pos):
        if is_pos:
            continue
        ann = f": {ast.unparse(arg.annotation)}" if arg.annotation else ""
        default_val = ""
        if idx >= defaults_offset:
            default_val = f" = {ast.unparse(defaults[idx - defaults_offset])}"
        args_list.append(f"{arg.arg}{ann}{default_val}")
        
    if node.args.vararg:
        ann = f": {ast.unparse(node.args.vararg.annotation)}" if node.args.vararg.annotation else ""
        args_list.append(f"*{node.args.vararg.arg}{ann}")
        
    # Keyword-only arguments
    kwonly = getattr(node.args, "kwonlyargs", [])
    kw_defaults = getattr(node.args, "kw_defaults", [])
    if kwonly and not node.args.vararg:
        args_list.append("*")
    for idx, arg in enumerate(kwonly):
        ann = f": {ast.unparse(arg.annotation)}" if arg.annotation else ""
        default_val = ""
        if idx < len(kw_defaults) and kw_defaults[idx] is not None:
            default_val = f" = {ast.unparse(kw_defaults[idx])}"
        args_list.append(f"{arg.arg}{ann}{default_val}")
        
    if node.args.kwarg:
        ann = f": {ast.unparse(node.args.kwarg.annotation)}" if node.args.kwarg.annotation else ""
        args_list.append(f"**{node.args.kwarg.arg}{ann}")
        
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    ret = f"{prefix} {node.name}({', '.join(args_list)})"
    if node.returns:
        ret += f" -> {ast.unparse(node.returns)}"
    return ret

def get_class_signature(node: ast.ClassDef) -> str:
    """Reconstructs the class signature using ast.unparse."""
    bases = [ast.unparse(base) for base in node.bases]
    bases_str = f"({', '.join(bases)})" if bases else ""
    return f"class {node.name}{bases_str}"


class AstCodeParserVisitor(ast.NodeVisitor):
    """Visitor to collect codebase semantic chunks with context tracking."""
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.chunks: List[CodeChunk] = []
        self.current_class: Optional[str] = None

    def visit_ClassDef(self, node: ast.ClassDef):
        class_type = classify_class(node)
        start_line = node.lineno
        end_line = getattr(node, "end_lineno", start_line)
        docstring = ast.get_docstring(node) or ""
        
        self.chunks.append(CodeChunk(
            id=f"{self.filepath}::{node.name}",
            name=node.name,
            type=class_type,
            signature=get_class_signature(node),
            docstring=docstring.strip(),
            start_line=start_line,
            end_line=end_line
        ))
        
        # Track class context to properly label methods
        prev_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = prev_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._process_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._process_function(node)

    def _process_function(self, node: ast.AST):
        func_type = classify_function(node)
        start_line = node.lineno
        end_line = getattr(node, "end_lineno", start_line)
        docstring = ast.get_docstring(node) or ""
        
        # Reconstruct name & ID based on class context
        if self.current_class:
            name = f"{self.current_class}.{node.name}"
            chunk_id = f"{self.filepath}::{self.current_class}.{node.name}"
        else:
            name = node.name
            chunk_id = f"{self.filepath}::{node.name}"
            
        self.chunks.append(CodeChunk(
            id=chunk_id,
            name=name,
            type=func_type,
            signature=get_function_signature(node),
            docstring=docstring.strip(),
            start_line=start_line,
            end_line=end_line
        ))
        self.generic_visit(node)


class AstCodeParser(CodeParserGateway):
    def parse_file(self, filepath: str) -> List[CodeChunk]:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source, filename=filepath)
            
            visitor = AstCodeParserVisitor(filepath)
            visitor.visit(tree)
            return visitor.chunks
        except Exception as e:
            raise ParserError(f"Failed to parse python file {filepath}: {e}") from e
