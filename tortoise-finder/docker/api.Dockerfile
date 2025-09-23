FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml /app/
RUN pip install -U pip && pip install -e .
COPY api /app/api
COPY pipeline /app/pipeline
COPY models /app/models
COPY storage /app/storage
COPY scripts /app/scripts
ENV PYTHONUNBUFFERED=1
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
