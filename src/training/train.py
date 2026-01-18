import logging
import shutil
from pathlib import Path
from typing import Optional
from ultralytics import YOLO

logger = logging.getLogger(__name__)

class ModelTrainer:
    """
    Handles the training of the YOLOv8 model.
    """

    def __init__(self, model_name: str = "yolov8n.pt", output_dir: Path = Path("models")):
        """
        Args:
            model_name (str): Name of the YOLO model to start with (e.g., yolov8n.pt).
            output_dir (Path): Directory where the trained model will be exported.
        """
        self.model_name = model_name
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.model = YOLO(self.model_name)

    def train(self, data_yaml: Path, epochs: int = 50, img_size: int = 640) -> Path:
        """
        Runs the training process.

        Args:
            data_yaml (Path): Path to the data.yaml file.
            epochs (int): Number of training epochs.
            img_size (int): Image size.
        
        Returns:
            Path: Path to the best trained model.
        """
        logger.info(f"Starting training for {epochs} epochs using {data_yaml}...")
        
        # Train model
        results = self.model.train(
            data=str(data_yaml),
            epochs=epochs,
            imgsz=img_size,
            project=str(self.output_dir),
            name="train_run",
            exist_ok=True
        )
        
        # Retrieve best model path
        # Ultralytics saves to project/name/weights/best.pt
        best_model_path = self.output_dir / "train_run" / "weights" / "best.pt"
        
        if best_model_path.exists():
            logger.info(f"Training complete. Best model saved at {best_model_path}")
            return best_model_path
        else:
            logger.error("Training completed but 'best.pt' was not found.")
            raise FileNotFoundError("best.pt not found after training.")

    def publish_model(self, source_path: Path, version: str = "v1") -> Path:
        """
        Publishes (renames/moves) the trained model to the main models directory.

        Args:
            source_path (Path): Path to the trained best.pt.
            version (str): Version tag.

        Returns:
            Path: Path to the published model.
        """
        final_name = f"yolo_stride_{version}.pt"
        destination = self.output_dir / final_name
        shutil.copy2(source_path, destination)
        logger.info(f"Model published to {destination}")
        return destination
