"""
Training dataset management utilities.
"""

import os
import pandas as pd
import tempfile
from typing import List, Dict, Any
from storage.io import client, get_url
from storage.paths import training_dataset_key, training_image_key

class TrainingDataset:
    """Manage training datasets stored in S3."""
    
    def __init__(self, version: str = "v1.0"):
        self.version = version
        self.bucket = os.environ.get("ARTIFACT_BUCKET", "tortoise-artifacts")
        self.s3_client = client()
    
    def create_dataset(self, split: str, image_list: List[Dict[str, Any]]) -> str:
        """
        Create a training dataset from a list of images.
        
        Args:
            split: Dataset split (train, val, test)
            image_list: List of image metadata dictionaries
            
        Returns:
            S3 key of the created dataset
        """
        df = pd.DataFrame(image_list)
        
        # Add S3 URLs for images
        df['image_url'] = df.apply(
            lambda row: get_url(self.bucket, training_image_key(row['filename'], 'raw', row['label'])), 
            axis=1
        )
        
        # Save to parquet
        dataset_key = training_dataset_key(self.version, split)
        
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
            df.to_parquet(tmp.name, index=False)
            
            from storage.io import put_file
            put_file(self.bucket, dataset_key, tmp.name, "application/octet-stream")
            os.unlink(tmp.name)
        
        print(f"Created dataset: {dataset_key}")
        return dataset_key
    
    def load_dataset(self, split: str) -> pd.DataFrame:
        """
        Load a training dataset from S3.
        
        Args:
            split: Dataset split (train, val, test)
            
        Returns:
            DataFrame containing the dataset
        """
        dataset_key = training_dataset_key(self.version, split)
        
        try:
            obj = self.s3_client.get_object(self.bucket, dataset_key)
            with tempfile.NamedTemporaryFile(suffix='.parquet') as tmp:
                with open(tmp.name, 'wb') as f:
                    f.write(obj.read())
                return pd.read_parquet(tmp.name)
        except Exception as e:
            print(f"Failed to load dataset {split}: {e}")
            return pd.DataFrame()
    
    def list_datasets(self) -> List[str]:
        """List all available dataset versions."""
        try:
            datasets = []
            prefix = f"training/datasets/"
            for obj in self.s3_client.list_objects(self.bucket, prefix=prefix, recursive=True):
                if obj.object_name.endswith('.parquet'):
                    # Extract version from path
                    parts = obj.object_name.split('/')
                    if len(parts) >= 3:
                        version = parts[2]
                        if version not in datasets:
                            datasets.append(version)
            return datasets
        except Exception as e:
            print(f"Failed to list datasets: {e}")
            return []
    
    def get_dataset_info(self, split: str) -> Dict[str, Any]:
        """Get information about a dataset split."""
        df = self.load_dataset(split)
        if df.empty:
            return {"error": f"Dataset {split} not found"}
        
        return {
            "version": self.version,
            "split": split,
            "total_images": len(df),
            "positive_count": len(df[df['label'] == 'positive']) if 'label' in df.columns else 0,
            "negative_count": len(df[df['label'] == 'negative']) if 'label' in df.columns else 0,
            "columns": list(df.columns)
        }

def get_training_dataset(version: str = "v1.0") -> TrainingDataset:
    """Factory function to get a training dataset instance."""
    return TrainingDataset(version)
