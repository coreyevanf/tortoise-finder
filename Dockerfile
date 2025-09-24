FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

COPY requirements-demo.txt ./
RUN pip install --no-cache-dir -r requirements-demo.txt

COPY tortoise-finder/ ./

EXPOSE ${PORT}

CMD ["python", "demo_server.py"]
