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

    def train(self, data_yaml: Path, epochs: int = 50, img_size: int = 640, 
              patience: int = 50, batch: int = 16, workers: int = 8, cache: bool = True) -> Path:
        """
        Runs the training process with automatic resume detection.
        
        Resume behavior:
        - If a checkpoint exists and training was INTERRUPTED (epoch < target), resume automatically
        - If a checkpoint exists but training was COMPLETED, start fresh training
        - If no checkpoint exists, start fresh training

        Args:
            data_yaml (Path): Path to the data.yaml file.
            epochs (int): Number of training epochs.
            img_size (int): Image size.
            patience (int): Epochs to wait for no improvement before stopping.
            batch (int): Batch size.
            workers (int): Number of worker threads for data loading.
            cache (bool): Whether to cache images in RAM (True) or disk (False).
        
        Returns:
            Path: Path to the best trained model.
        """
        logger.info(f"Starting training for {epochs} epochs using {data_yaml}...")
        logger.info(f"Performance tuning: Batch={batch}, Workers={workers}, Cache={cache}, Patience={patience}")
        
        last_ckpt = self.output_dir / "train_run" / "weights" / "last.pt"
        args_yaml = self.output_dir / "train_run" / "args.yaml"
        
        should_resume = False
        
        # Check if we should resume from an interrupted training
        if last_ckpt.exists() and args_yaml.exists():
            try:
                import yaml
                with open(args_yaml, 'r') as f:
                    saved_args = yaml.safe_load(f)
                
                saved_epochs = saved_args.get('epochs', 0)
                
                # Check results.csv to see how many epochs were completed
                results_csv = self.output_dir / "train_run" / "results.csv"
                if results_csv.exists():
                    import pandas as pd
                    df = pd.read_csv(results_csv)
                    completed_epochs = len(df)
                    
                    if completed_epochs < saved_epochs:
                        # Training was interrupted - resume
                        logger.info(f"Detected interrupted training: {completed_epochs}/{saved_epochs} epochs completed")
                        should_resume = True
                    else:
                        # Training completed - check if user wants more epochs
                        if epochs > saved_epochs:
                            logger.info(f"Previous training completed {saved_epochs} epochs. Starting fresh with {epochs} epochs.")
                        else:
                            logger.info(f"Previous training already completed {completed_epochs} epochs. Starting fresh training.")
                else:
                    # No results.csv but checkpoint exists - might be corrupted, start fresh
                    logger.warning("Checkpoint exists but no results.csv found. Starting fresh training.")
            except Exception as e:
                logger.warning(f"Could not read training state: {e}. Starting fresh training.")
        
        if should_resume:
            logger.info(f"Resuming training from checkpoint: {last_ckpt}")
            self.model = YOLO(last_ckpt)
            results = self.model.train(resume=True)
        else:
            # Fresh training - use the pretrained base model
            self.model = YOLO(self.model_name)
            
            results = self.model.train(
                data=str(data_yaml),
                epochs=epochs,
                imgsz=img_size,
                patience=patience,
                batch=batch,
                workers=workers,
                cache=cache,
                project=str(self.output_dir),
                name="train_run",
                exist_ok=True,
                plots=True,
                # Enhanced augmentation for better icon recognition
                hsv_h=0.015,      # Color hue variation
                hsv_s=0.7,        # Saturation variation  
                hsv_v=0.4,        # Value variation
                scale=0.9,        # Scale variation (important for icons)
                mosaic=1.0,       # Mosaic augmentation
                mixup=0.1,        # Mixup for generalization
                copy_paste=0.1,   # Copy-paste augmentation
            )
        
        # Retrieve best model path
        best_model_path = self.output_dir / "train_run" / "weights" / "best.pt"
        
        if best_model_path.exists():
            logger.info(f"Training complete. Best model saved at {best_model_path}")
            self._evaluate_and_log(best_model_path)
            return best_model_path
        else:
            logger.error("Training completed but 'best.pt' was not found.")
            raise FileNotFoundError("best.pt not found after training.")

    def _evaluate_and_log(self, model_path: Path) -> None:
        """
        Runs validation and logs performance metrics.
        """
        try:
            # 1. Validation Metrics (mAP)
            logger.info("Running validation to calculate accuracy (mAP)...")
            val_results = self.model.val(split='val')
            
            # map50: Mean Average Precision at IoU=0.5
            # map50-95: Mean Average Precision at IoU=[0.5:0.95]
            map50 = val_results.box.map50
            map50_95 = val_results.box.map
            
            logger.info(f"Validation Accuracy (mAP@50): {map50:.4f}")
            logger.info(f"Validation Accuracy (mAP@50-95): {map50_95:.4f}")
            
            # 2. Training Losses (from results.csv)
            results_csv = self.output_dir / "train_run" / "results.csv"
            if results_csv.exists():
                import pandas as pd
                # Read CSV, stripping whitespace from column names
                df = pd.read_csv(results_csv)
                df.columns = df.columns.str.strip()
                
                # Get last epoch metrics
                last_epoch = df.iloc[-1]
                train_box_loss = last_epoch.get('train/box_loss', 0)
                train_cls_loss = last_epoch.get('train/cls_loss', 0)
                val_box_loss = last_epoch.get('val/box_loss', 0)
                val_cls_loss = last_epoch.get('val/cls_loss', 0)
                
                logger.info("Training Metrics (Last Epoch):")
                logger.info(f"  - Train Box Loss: {train_box_loss:.4f}")
                logger.info(f"  - Train Class Loss: {train_cls_loss:.4f}")
                logger.info(f"  - Val Box Loss: {val_box_loss:.4f}")
                logger.info(f"  - Val Class Loss: {val_cls_loss:.4f}")
            
        except Exception as e:
            logger.warning(f"Failed to log detailed metrics: {e}")


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
