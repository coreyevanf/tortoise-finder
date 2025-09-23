FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml /app/
RUN pip install -U pip && pip install -e .
COPY app_ui /app/app_ui
ENV PYTHONUNBUFFERED=1
CMD ["python", "app_ui/ui.py"]
