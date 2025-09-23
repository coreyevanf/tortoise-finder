FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml /app/
RUN pip install -U pip && pip install -e .
COPY worker.py /app/worker.py
COPY pipeline /app/pipeline
COPY models /app/models
COPY storage /app/storage
COPY api/schemas.py /app/api/schemas.py
ENV PYTHONUNBUFFERED=1
CMD ["python", "worker.py"]
