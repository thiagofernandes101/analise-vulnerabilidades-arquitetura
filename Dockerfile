FROM python:3.10-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

ENV PORT=8080
EXPOSE 8080

# Run with gunicorn for production
# Shell form so $PORT is expanded; `exec` ensures gunicorn receives SIGTERM from Cloud Run.
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 src.main:app
