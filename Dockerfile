FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y gcc libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*



# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Default command (can be overridden by compose)
CMD ["python", "src/main.py"]
