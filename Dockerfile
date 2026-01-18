FROM python:3.10-slim

WORKDIR /app

# Install system dependencies if needed (e.g., for some python packages)
# RUN apt-get update && apt-get install -y gcc

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Default command (can be overridden by compose)
CMD ["python", "src/main.py"]
