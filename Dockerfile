FROM python:3.12-slim
# Cache bust: 2026-07-19 15:54

# Install git
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

# Copy source code
COPY src/ ./src/
COPY main.py ./

# Configure python path
ENV PYTHONPATH=/app

ENTRYPOINT ["python", "/app/main.py"]
