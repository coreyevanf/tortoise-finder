from datetime import datetime

def run_prefix(run_id: str) -> str: 
    return f"runs/{run_id}"

def results_key(run_id: str) -> str: 
    return f"{run_prefix(run_id)}/results.parquet"

def geojson_key(run_id: str) -> str: 
    return f"{run_prefix(run_id)}/positives.geojson"

def thumbs_prefix(run_id: str) -> str: 
    return f"{run_prefix(run_id)}/thumbs"

def dataset_prefix(name_or_uri: str) -> str: 
    return f"datasets/{name_or_uri.strip('/')}"

def model_prefix(version: str = "production") -> str:
    return f"models/{version}"

def model_weights_key(version: str = "production") -> str:
    return f"{model_prefix(version)}/model.pth"

def model_config_key(version: str = "production") -> str:
    return f"{model_prefix(version)}/config.json"

def model_metadata_key(version: str = "production") -> str:
    return f"{model_prefix(version)}/metadata.json"

def training_prefix() -> str:
    return "training"

def training_images_prefix(split: str = "raw") -> str:
    return f"{training_prefix()}/{split}/images"

def training_annotations_prefix(split: str = "raw") -> str:
    return f"{training_prefix()}/{split}/annotations"

def training_processed_prefix() -> str:
    return f"{training_prefix()}/processed"

def training_dataset_prefix(version: str = "v1.0") -> str:
    return f"{training_prefix()}/datasets/{version}"

def training_image_key(image_id: str, split: str = "raw", label: str = "positive") -> str:
    return f"{training_images_prefix(split)}/{label}/{image_id}"

def training_annotation_key(image_id: str, split: str = "raw", label: str = "positive") -> str:
    return f"{training_annotations_prefix(split)}/{label}/{image_id}.json"

def training_dataset_key(dataset_version: str, split: str) -> str:
    return f"{training_dataset_prefix(dataset_version)}/{split}.parquet"

def now_id() -> str: 
    return datetime.utcnow().strftime("%Y%m%d-%H%M%S")
