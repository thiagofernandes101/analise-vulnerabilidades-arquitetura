#!/usr/bin/env python3
"""
Dataset Merger for STRIDE-YOLO Training

This script merges multiple YOLO-format datasets for combined training.
It handles:
1. Copying images from multiple sources
2. Merging/converting annotations
3. Creating a unified data.yaml

Usage:
    python src/training/merge_datasets.py --output dataset/merged
"""
import argparse
import logging
import shutil
import yaml
from pathlib import Path
from collections import defaultdict
from typing import Dict, Set, Tuple, List

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DatasetMerger:
    """Merges multiple YOLO-format datasets."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.all_classes: Set[str] = set()
        self.class_to_id: Dict[str, int] = {}
        self.stats = defaultdict(int)
        
    def _read_class_names(self, data_yaml: Path) -> Dict[int, str]:
        """Read class names from a data.yaml file."""
        if not data_yaml.exists():
            return {}
        
        with open(data_yaml) as f:
            data = yaml.safe_load(f)
        
        names = data.get('names', [])
        if isinstance(names, list):
            return {i: name for i, name in enumerate(names)}
        elif isinstance(names, dict):
            return {int(k): v for k, v in names.items()}
        return {}
    
    def _load_roboflow_dataset(self, dataset_dir: Path, split: str = 'train') -> Tuple[List[Path], List[Path], Dict[int, str]]:
        """Load a Roboflow-exported YOLO dataset."""
        images_dir = dataset_dir / split / 'images'
        labels_dir = dataset_dir / split / 'labels'
        
        if not images_dir.exists():
            logger.warning(f"Images directory not found: {images_dir}")
            return [], [], {}
        
        images = list(images_dir.glob('*.[jp][pn][g]'))
        labels = [labels_dir / (img.stem + '.txt') for img in images]
        
        # Try to find class names (data.yaml or classes.txt)
        data_yaml = dataset_dir / 'data.yaml'
        classes_txt = dataset_dir / 'classes.txt'
        
        class_map = {}
        if data_yaml.exists():
            class_map = self._read_class_names(data_yaml)
        elif classes_txt.exists():
            with open(classes_txt) as f:
                for i, line in enumerate(f):
                    class_map[i] = line.strip()
        
        return images, labels, class_map
    
    def _load_pascal_voc_dataset(self, dataset_dir: Path) -> Tuple[List[Path], List[Path], Dict[str, str]]:
        """Load Pascal VOC format dataset (from original dataset_augmented)."""
        images = list(dataset_dir.glob('*.png')) + list(dataset_dir.glob('*.jpg'))
        annotations = [img.with_suffix('.xml') for img in images]
        
        # Extract class names from annotations
        class_names = set()
        for ann in annotations[:100]:  # Sample first 100 for speed
            if ann.exists():
                import xml.etree.ElementTree as ET
                try:
                    tree = ET.parse(ann)
                    for obj in tree.findall('.//object/name'):
                        class_names.add(obj.text)
                except:
                    pass
        
        return images, annotations, {name: name for name in class_names}
    
    def collect_all_classes(self, datasets: List[Dict]) -> Dict[str, int]:
        """Collect all unique class names and assign unified IDs."""
        all_classes = set()
        
        for ds in datasets:
            if ds['format'] == 'yolo':
                _, _, class_map = self._load_roboflow_dataset(ds['path'])
                all_classes.update(class_map.values())
            elif ds['format'] == 'voc':
                _, _, class_map = self._load_pascal_voc_dataset(ds['path'])
                all_classes.update(class_map.values())
        
        # Sort and assign IDs
        sorted_classes = sorted(all_classes)
        self.class_to_id = {name: i for i, name in enumerate(sorted_classes)}
        self.all_classes = set(sorted_classes)
        
        logger.info(f"Total unique classes: {len(self.class_to_id)}")
        return self.class_to_id
    
    def merge(self, datasets: List[Dict], val_split: float = 0.2):
        """
        Merge multiple datasets into a unified YOLO format.
        
        Args:
            datasets: List of dicts with 'path', 'name', and 'format' keys
            val_split: Fraction to use for validation
        """
        # Create output structure
        train_images = self.output_dir / 'train' / 'images'
        train_labels = self.output_dir / 'train' / 'labels'
        val_images = self.output_dir / 'val' / 'images'
        val_labels = self.output_dir / 'val' / 'labels'
        
        for d in [train_images, train_labels, val_images, val_labels]:
            d.mkdir(parents=True, exist_ok=True)
        
        all_pairs = []  # (image_path, label_path, class_map, original_format)
        
        # Collect all data
        for ds in datasets:
            ds_path = Path(ds['path'])
            ds_name = ds['name']
            ds_format = ds['format']
            
            logger.info(f"Processing dataset: {ds_name}")
            
            if ds_format == 'yolo':
                # Process train and test splits
                for split in ['train', 'test']:
                    images, labels, class_map = self._load_roboflow_dataset(ds_path, split)
                    for img, lbl in zip(images, labels):
                        if img.exists():
                            all_pairs.append((img, lbl, class_map, 'yolo', ds_name))
                            self.stats[f'{ds_name}_{split}'] += 1
            
            elif ds_format == 'voc':
                images, annotations, class_map = self._load_pascal_voc_dataset(ds_path)
                for img, ann in zip(images, annotations):
                    if img.exists() and ann.exists():
                        all_pairs.append((img, ann, class_map, 'voc', ds_name))
                        self.stats[ds_name] += 1
        
        logger.info(f"Total samples collected: {len(all_pairs)}")
        
        # Shuffle and split
        import random
        random.shuffle(all_pairs)
        split_idx = int(len(all_pairs) * (1 - val_split))
        train_pairs = all_pairs[:split_idx]
        val_pairs = all_pairs[split_idx:]
        
        # Copy and convert
        self._copy_pairs(train_pairs, train_images, train_labels)
        self._copy_pairs(val_pairs, val_images, val_labels)
        
        # Generate data.yaml
        self._generate_data_yaml()
        
        logger.info(f"Merge complete!")
        logger.info(f"  Train: {len(train_pairs)} images")
        logger.info(f"  Val: {len(val_pairs)} images")
        logger.info(f"  Classes: {len(self.class_to_id)}")
        
        for key, count in sorted(self.stats.items()):
            logger.info(f"  {key}: {count}")
    
    def _copy_pairs(self, pairs: List, images_dir: Path, labels_dir: Path):
        """Copy images and convert/copy labels."""
        for i, (img_path, label_path, class_map, fmt, ds_name) in enumerate(pairs):
            # Unique filename to avoid collisions
            new_name = f"{ds_name}_{i:06d}{img_path.suffix}"
            
            # Copy image
            shutil.copy(img_path, images_dir / new_name)
            
            # Handle label
            label_new_name = f"{ds_name}_{i:06d}.txt"
            
            if fmt == 'yolo':
                self._convert_yolo_label(label_path, labels_dir / label_new_name, class_map)
            elif fmt == 'voc':
                self._convert_voc_label(label_path, labels_dir / label_new_name, img_path)
    
    def _convert_yolo_label(self, src: Path, dst: Path, class_map: Dict[int, str]):
        """Convert YOLO label with class ID remapping."""
        if not src.exists():
            # Create empty label file
            dst.touch()
            return
        
        lines = []
        with open(src) as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 5:
                    old_id = int(parts[0])
                    class_name = class_map.get(old_id, f"unknown_{old_id}")
                    new_id = self.class_to_id.get(class_name, 0)
                    parts[0] = str(new_id)
                    lines.append(' '.join(parts))
        
        with open(dst, 'w') as f:
            f.write('\n'.join(lines))
    
    def _convert_voc_label(self, src: Path, dst: Path, img_path: Path):
        """Convert Pascal VOC XML to YOLO format."""
        import xml.etree.ElementTree as ET
        from PIL import Image
        
        if not src.exists():
            dst.touch()
            return
        
        # Get image dimensions
        try:
            with Image.open(img_path) as im:
                img_w, img_h = im.size
        except:
            img_w, img_h = 640, 640
        
        tree = ET.parse(src)
        root = tree.getroot()
        
        lines = []
        for obj in root.findall('.//object'):
            name = obj.find('name').text
            bbox = obj.find('bndbox')
            
            xmin = float(bbox.find('xmin').text)
            ymin = float(bbox.find('ymin').text)
            xmax = float(bbox.find('xmax').text)
            ymax = float(bbox.find('ymax').text)
            
            # Convert to YOLO format (center_x, center_y, width, height - normalized)
            x_center = ((xmin + xmax) / 2) / img_w
            y_center = ((ymin + ymax) / 2) / img_h
            width = (xmax - xmin) / img_w
            height = (ymax - ymin) / img_h
            
            class_id = self.class_to_id.get(name, 0)
            lines.append(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}")
        
        with open(dst, 'w') as f:
            f.write('\n'.join(lines))
    
    def _generate_data_yaml(self):
        """Generate unified data.yaml."""
        # Sort classes by ID
        sorted_classes = sorted(self.class_to_id.items(), key=lambda x: x[1])
        names = [name for name, _ in sorted_classes]
        
        data = {
            'names': names,
            'nc': len(names),
            'train': str(self.output_dir / 'train' / 'images'),
            'val': str(self.output_dir / 'val' / 'images'),
        }
        
        yaml_path = self.output_dir / 'data.yaml'
        with open(yaml_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Created {yaml_path}")


def main():
    parser = argparse.ArgumentParser(description='Merge YOLO datasets')
    parser.add_argument('--output', type=str, default='dataset/merged',
                        help='Output directory for merged dataset')
    args = parser.parse_args()
    
    base_dir = Path(__file__).resolve().parent.parent.parent
    output_dir = base_dir / args.output
    
    # Clean output directory
    if output_dir.exists():
        shutil.rmtree(output_dir)
    
    # Define datasets to merge
    datasets = [
        {
            'name': 'original',
            'path': base_dir / 'dataset' / 'dataset_augmented',
            'format': 'voc'  # Pascal VOC format
        },
        {
            'name': 'aws_icon_detector',
            'path': base_dir / 'dataset' / 'AWS Icon Detector.v4-aws_icon_detector.yolov8',
            'format': 'yolo'
        },
        {
            'name': 'aws_system_diagrams',
            'path': base_dir / 'dataset' / 'AWS System diagrams.v1i.yolov8',
            'format': 'yolo'
        },
    ]
    
    merger = DatasetMerger(output_dir)
    
    # First pass: collect all classes
    logger.info("Collecting class names from all datasets...")
    merger.collect_all_classes(datasets)
    
    # Second pass: merge datasets
    logger.info("Merging datasets...")
    merger.merge(datasets, val_split=0.2)
    
    logger.info("Done!")


if __name__ == '__main__':
    main()
