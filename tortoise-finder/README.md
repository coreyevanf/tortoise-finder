# Tortoise Finder

A web and CLI application for detecting tortoises in aerial imagery using machine learning. The system provides a complete pipeline from dataset selection to result export, with a modern web interface and offline-capable deployment.

## 🎯 Project Overview

Tortoise Finder is designed to:
1. **Select datasets** (local folders or S3-compatible storage)
2. **Run model inference** on aerial imagery
3. **Review detections** with adjustable confidence thresholds
4. **Confirm/reject hits** through an interactive interface
5. **Export results** in multiple formats (GeoJSON, CSV, GPX, KML)

## 🏗️ Architecture

The system is built with a microservices architecture:

- **FastAPI** - REST API backend
- **Gradio** - Web UI for interactive review
- **RQ + Redis** - Job queue for long-running inference tasks
- **MinIO** - S3-compatible object storage (switchable to AWS S3)
- **MLflow** - Model registry and experiment tracking
- **Docker Compose** - Containerized deployment

## Quick Start

### Prerequisites

- Docker Desktop installed and running
- Git

### 1. Clone and Setup

```bash
git clone <repository-url>
cd tortoise-finder
```

### 2. Start the System

```bash
cd docker
docker compose up --build
```

This will start all services:
- **Redis** (port 6379) - Job queue
- **MinIO** (ports 9000, 9001) - Object storage
- **API** (port 8000) - FastAPI backend
- **Worker** - Background job processor
- **UI** (port 7860) - Gradio web interface

### 3. Access the Application

- **Web UI**: http://localhost:7860
- **API Documentation**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)

### 4. Run Your First Detection

1. Open the web UI at http://localhost:7860
2. Leave the default dataset URI: `s3://tortoise-artifacts/datasets/demo`
3. Click "Start Run" to begin inference
4. Watch the status update as the job progresses
5. Adjust the threshold slider to filter results
6. Export results in your preferred format

## 📁 Project Structure

```
tortoise-finder/
├── README.md                 # This file
├── .gitignore               # Git ignore rules
├── .env                     # Environment variables
├── pyproject.toml           # Python dependencies
├── docker/                  # Docker configuration
│   ├── docker-compose.yml   # Service orchestration
│   ├── api.Dockerfile       # API service container
│   ├── worker.Dockerfile    # Worker service container
│   └── ui.Dockerfile        # UI service container
├── app_ui/                  # Gradio web interface
│   └── ui.py               # Main UI application
├── api/                     # FastAPI backend
│   ├── main.py             # API routes and endpoints
│   ├── schemas.py          # Pydantic data models
│   └── deps.py             # Dependency injection
├── pipeline/                # ML pipeline components
│   ├── run.py              # Main inference job runner
│   ├── infer.py            # Model inference (placeholder)
│   ├── tiler.py            # Image tiling (placeholder)
│   ├── postproc.py         # Post-processing (placeholder)
│   ├── export.py           # Result export utilities
│   └── utils.py            # Pipeline utilities
├── models/                  # Model management
│   └── loader.py           # Model loading utilities
├── storage/                 # Object storage abstraction
│   ├── io.py               # MinIO/S3 operations
│   └── paths.py            # Path utilities
├── cli/                     # Command-line interface
│   └── main.py             # Typer CLI application
├── scripts/                 # Utility scripts
│   └── seed_fake_dataset.py # Dataset seeding script
├── tests/                   # Test suite
│   ├── test_api.py         # API tests
│   └── test_pipeline.py    # Pipeline tests
└── worker.py               # RQ worker process
```

## 🔧 Configuration

### Environment Variables

The system uses the following environment variables (configured in `.env`):

```bash
# Storage Configuration
ARTIFACT_BUCKET=tortoise-artifacts
S3_ENDPOINT=http://minio:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_REGION=us-east-1
S3_SECURE=false

# Redis/RQ Configuration
REDIS_URL=redis://redis:6379/0
RQ_QUEUE=tortoise

# MLflow Configuration
MLFLOW_TRACKING_URI=file:/mlruns

# Default Dataset
DEFAULT_DATASET_URI=s3://tortoise-artifacts/datasets/demo
```

### Switching to AWS S3

To use AWS S3 instead of MinIO:

```bash
S3_ENDPOINT=https://s3.amazonaws.com
S3_ACCESS_KEY=your_aws_access_key
S3_SECRET_KEY=your_aws_secret_key
S3_SECURE=true
```

## 🖥️ Usage

### Web Interface

The Gradio web interface provides:

- **Dataset Selection**: Choose local folders or S3 URIs
- **Threshold Control**: Adjust confidence threshold with a slider
- **Progress Monitoring**: Real-time job status updates
- **Result Gallery**: Browse detections with thumbnails
- **Export Options**: Download results in multiple formats

### Command Line Interface

```bash
# Start a new inference run
python -m cli.main run s3://bucket/dataset --threshold 0.8

# Check job status
python -m cli.main status <job_id>

# Export results
python -m cli.main export <run_id> --fmt geojson

# List positive detections
python -m cli.main positives <run_id> --threshold 0.8 --page 1
```

### API Endpoints

- `POST /run` - Start a new inference job
- `GET /status/{job_id}` - Check job progress
- `GET /positives` - List positive detections
- `POST /confirm` - Confirm/reject detections
- `GET /export` - Export results

See http://localhost:8000/docs for complete API documentation.

## 🔬 Model Integration

The current implementation uses placeholder models that generate random scores. To integrate real models:

### 1. Update Model Loading

Replace `models/loader.py` with your model loading logic:

```python
def load_model(self) -> bool:
    # Load your actual model weights
    self.model = torch.load('path/to/model.pth')
    return True
```

### 2. Implement Inference

Update `pipeline/infer.py` with your inference logic:

```python
def run_inference(tiles, model_version="production"):
    # Run actual model inference
    results = model.predict(tiles)
    return results
```

### 3. Update Pipeline

Modify `pipeline/run.py` to use real inference instead of random scores.

### Required Schema

Maintain this Parquet schema for results:
- `tile_id`: str - Unique tile identifier
- `score`: float - Confidence score (0.0-1.0)
- `lat`: float - Latitude coordinate
- `lon`: float - Longitude coordinate
- `thumb_url`: str - Thumbnail image URL
- `image_url`: str - Full image URL
- `model_ver`: str - Model version used
- `run_id`: str - Run identifier

## 🧪 Testing

Run the test suite:

```bash
# Install in development mode
pip install -e .

# Run tests
pytest tests/
```

## 🚢 Deployment

### Local Development

```bash
# Start all services
docker compose up --build

# View logs
docker compose logs -f

# Stop services
docker compose down
```

### Production Deployment

For production use:

1. **Security**: Add authentication to the web UI
2. **Scaling**: Use multiple worker instances
3. **Monitoring**: Add health checks and metrics
4. **Storage**: Configure persistent volumes
5. **Networking**: Set up proper ingress/egress rules

### Field Deployment

For offline field use:

1. Set `S3_ENDPOINT=http://host.docker.internal:9000` for external MinIO access
2. Use local storage volumes for persistence
3. Configure appropriate resource limits
4. Set up backup procedures for results

## 🔍 Troubleshooting

### Common Issues

**Services won't start:**
- Ensure Docker Desktop is running
- Check port conflicts (8000, 7860, 9000, 9001, 6379)
- Verify `.env` file exists and is properly formatted

**Jobs stuck in queue:**
- Check worker logs: `docker compose logs worker`
- Verify Redis connection
- Ensure MinIO is accessible

**Export fails:**
- Check MinIO console for bucket permissions
- Verify file paths and formats
- Check worker logs for processing errors

**UI not loading:**
- Verify API service is running: `curl http://localhost:8000/docs`
- Check browser console for errors
- Ensure all services are healthy

### Logs

View service logs:

```bash
# All services
docker compose logs

# Specific service
docker compose logs api
docker compose logs worker
docker compose logs ui
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

[Add your license information here]

## 🆘 Support

For issues and questions:
- Check the troubleshooting section
- Review API documentation at http://localhost:8000/docs
- Open an issue in the repository

---

**Note**: This is an MVP implementation with placeholder models. The system is designed to be easily extended with real ML models while maintaining the same interface and data formats.
