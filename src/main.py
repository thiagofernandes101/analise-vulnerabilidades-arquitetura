import argparse
import logging
import sys
import os
from pathlib import Path

# Ensure src is in path for module discovery
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("stride_yolo_main")

# Import Modules
from src.training.data_prep import DatasetConverter
from src.training.train import ModelTrainer
from src.inference.threat_model import ThreatModeler


def run_training_pipeline(args):
    """
    Executes the data preparation and training pipeline.
    """
    base_dir = Path(__file__).resolve().parent.parent
    models_dir = base_dir / "models"
    
    # Determine dataset path
    if args.dataset:
        # Use pre-merged/pre-prepared dataset
        data_yaml = Path(args.dataset) / "data.yaml"
        if not data_yaml.exists():
            logger.error(f"data.yaml not found in {args.dataset}")
            return
        logger.info(f"Using pre-prepared dataset: {args.dataset}")
    else:
        # Original flow: convert from VOC to YOLO format
        dataset_dir = base_dir / "dataset" / "dataset_augmented"
        yolo_data_dir = base_dir / "dataset" / "yolo_format"
        
        logger.info("Step 1: Preparing Data...")
        if not dataset_dir.exists():
            logger.error(f"Dataset directory not found: {dataset_dir}")
            return

        converter = DatasetConverter(source_dir=dataset_dir, output_dir=yolo_data_dir)
        converter.process(test_size=args.test_split)
        data_yaml = yolo_data_dir / "data.yaml"
        
        if not data_yaml.exists():
             logger.error("data.yaml not found. Data prep failed.")
             return
    
    # Train Model
    logger.info("Training Model...")
    trainer = ModelTrainer(model_name=args.model_name, output_dir=models_dir)

    # Training with automatic resume detection (handled internally by trainer)
    best_model = trainer.train(
        data_yaml=data_yaml, 
        epochs=args.epochs,
        img_size=args.imgsz,
        patience=args.patience,
        batch=args.batch,
        workers=args.workers,
        cache=not args.no_cache
    )
    
    # Publish Model
    published_model = trainer.publish_model(best_model, version="v1")
    logger.info(f"Pipeline finished. Model ready at {published_model}")


def run_inference_pipeline(args):
    """
    Executes the inference pipeline.
    """
    if not args.image:
        logger.error("Please provide an image path for inference using --image")
        return

    image_path = Path(args.image)
    if not image_path.exists():
        logger.error(f"Image not found: {image_path}")
        return
        
    base_dir = Path(__file__).resolve().parent.parent
    default_model = base_dir / "models" / "yolo_stride_v1.pt"
    
    model_path = Path(args.model_path) if args.model_path else default_model
    
    if not model_path.exists():
        logger.error(f"Model not found at {model_path}. Please train first.")
        return

    # Run Inference
    logger.info(f"Running inference on {image_path} using {model_path} at {args.imgsz}px...")
    modeler = ThreatModeler(model_path=model_path)
    analysis = modeler.analyze_image(image_path, conf_threshold=args.conf, imgsz=args.imgsz)
    
    # Generate Report
    output_report = image_path.with_name(f"{image_path.stem}_report.md")
    modeler.generate_report(analysis, output_report)
    logger.info(f"Analysis complete. Report: {output_report}")


def main():
    parser = argparse.ArgumentParser(description="STRIDE Threat Modeling with YOLO")
    subparsers = parser.add_subparsers(dest="mode", help="Mode of operation")

    # Train Command
    train_parser = subparsers.add_parser("train", help="Train the model")
    train_parser.add_argument("--dataset", type=str, help="Path to pre-prepared dataset (skips data prep)")
    train_parser.add_argument("--epochs", type=int, default=50, help="Number of epochs")
    train_parser.add_argument("--model-name", type=str, default="yolov8s.pt", help="Base model (yolov8n/s/m/l/x)")
    train_parser.add_argument("--imgsz", type=int, default=1280, help="Training image size")
    train_parser.add_argument("--test-split", type=float, default=0.2, help="Validation split size")
    train_parser.add_argument("--patience", type=int, default=15, help="Early stopping patience")
    train_parser.add_argument("--batch", type=int, default=4, help="Batch size (4 for 6GB VRAM, 8 for 8GB+)")
    train_parser.add_argument("--workers", type=int, default=4, help="Data loader workers")
    train_parser.add_argument("--no-cache", action="store_true", help="Disable RAM caching")

    # Inference Command
    inf_parser = subparsers.add_parser("inference", help="Run threat modeling on an image")
    inf_parser.add_argument("--image", type=str, required=True, help="Path to input image")
    inf_parser.add_argument("--model-path", type=str, help="Path to custom model .pt file")
    inf_parser.add_argument("--conf", type=float, default=0.20, help="Confidence threshold")
    inf_parser.add_argument("--imgsz", type=int, default=1280, help="Inference image size (larger = better for small icons)")

    # If no args provided (e.g. running from F5 without args), print help or default to a safe action
    if len(sys.argv) == 1:
        logger.info("No arguments provided. Running in default mode (help).")
        parser.print_help()
        # Alternatively, we could default to a loop for persistent debugging if 'APP_ENV' is set, 
        # but the request was to unify. Let's stick to CLI structure.
        return

    args = parser.parse_args()

    if args.mode == "train":
        run_training_pipeline(args)
    elif args.mode == "inference":
        run_inference_pipeline(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
