FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

# Install runtime dependencies
COPY requirements-demo.txt ./
RUN pip install --no-cache-dir -r requirements-demo.txt

# Copy application code and assets
COPY tortoise-finder /app

# Expose the port the app listens on
EXPOSE ${PORT}

CMD ["python", "demo_server.py"]
