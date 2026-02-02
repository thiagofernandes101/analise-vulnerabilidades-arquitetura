import logging
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
from collections import defaultdict
import yaml
from tqdm import tqdm
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)

class DatasetConverter:
    """
    Handles the conversion of an XML-annotated dataset into the YOLO (TXT) format.
    """

    def __init__(self, source_dir: Path, output_dir: Path):
        self.source_dir = source_dir
        self.output_dir = output_dir
        self.classes: List[str] = []
        self._class_map: Dict[str, int] = {}
        
        self.dirs = {
            'train_img': self.output_dir / 'train' / 'images',
            'train_lbl': self.output_dir / 'train' / 'labels',
            'val_img': self.output_dir / 'val' / 'images',
            'val_lbl': self.output_dir / 'val' / 'labels'
        }

    def _setup_directories(self) -> None:
        """Creates necessary output directories."""
        for path in self.dirs.values():
            path.mkdir(parents=True, exist_ok=True)

    def _extract_classes(self, xml_files: List[Path]) -> None:
        """Scans XML files to identify unique classes."""
        unique_classes: Set[str] = set()
        for xml_file in xml_files:
            try:
                tree = ET.parse(xml_file)
                for obj in tree.findall('object'):
                    name = obj.find('name')
                    if name is not None and name.text:
                        unique_classes.add(name.text)
            except ET.ParseError:
                logger.warning(f"Skipping malformed XML: {xml_file}")
        
        self.classes = sorted(list(unique_classes))
        self._class_map = {name: i for i, name in enumerate(self.classes)}
        logger.info(f"Found {len(self.classes)} classes")

    def _get_primary_class(self, xml_file: Path) -> Optional[str]:
        """Get the primary (first) class from an XML file for stratification."""
        try:
            tree = ET.parse(xml_file)
            for obj in tree.findall('object'):
                name = obj.find('name')
                if name is not None and name.text:
                    return name.text
        except ET.ParseError:
            pass
        return None

    def _stratified_split(self, xml_files: List[Path], test_size: float) -> Tuple[List[Path], List[Path]]:
        """
        Split files ensuring all classes are represented in both train and validation sets.
        Uses the primary class of each image for stratification.
        """
        # Group files by their primary class
        class_files: Dict[str, List[Path]] = defaultdict(list)
        unclassified = []
        
        for f in xml_files:
            primary_class = self._get_primary_class(f)
            if primary_class:
                class_files[primary_class].append(f)
            else:
                unclassified.append(f)
        
        train_files: List[Path] = []
        val_files: List[Path] = []
        classes_in_train: Set[str] = set()
        classes_in_val: Set[str] = set()
        
        for cls, files in class_files.items():
            if len(files) == 1:
                # Only one sample - put in training to ensure the model sees it
                train_files.extend(files)
                classes_in_train.add(cls)
                logger.debug(f"Class '{cls}' has only 1 sample - assigned to training")
            elif len(files) < 5:
                # Very few samples - ensure at least 1 goes to validation
                train_files.extend(files[:-1])
                val_files.append(files[-1])
                classes_in_train.add(cls)
                classes_in_val.add(cls)
            else:
                # Enough samples - split proportionally
                cls_train, cls_val = train_test_split(
                    files, test_size=test_size, random_state=42
                )
                train_files.extend(cls_train)
                val_files.extend(cls_val)
                classes_in_train.add(cls)
                classes_in_val.add(cls)
        
        # Handle unclassified files (split randomly)
        if unclassified:
            unc_train, unc_val = train_test_split(unclassified, test_size=test_size, random_state=42)
            train_files.extend(unc_train)
            val_files.extend(unc_val)
        
        # Log stratification results
        logger.info(f"Stratified split: {len(train_files)} train, {len(val_files)} val")
        logger.info(f"Classes in train: {len(classes_in_train)}, in val: {len(classes_in_val)}")
        
        missing_in_val = classes_in_train - classes_in_val
        if missing_in_val:
            logger.warning(f"Classes missing from validation set: {missing_in_val}")
        
        return train_files, val_files

    def _convert_bbox(self, size: Tuple[int, int], box: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
        """Converts VOC bbox to YOLO format."""
        dw = 1.0 / size[0]
        dh = 1.0 / size[1]
        x = (box[0] + box[1]) / 2.0
        y = (box[2] + box[3]) / 2.0
        w = box[1] - box[0]
        h = box[3] - box[2]
        return (x * dw, y * dh, w * dw, h * dh)

    def _process_file(self, xml_file: Path, img_dest: Path, lbl_dest: Path) -> None:
        """Converts a single XML/Image pair."""
        img_file = xml_file.with_suffix('.png')
        if not img_file.exists():
            return

        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            size = root.find('size')
            if size is None: return
            
            width = int(size.find('width').text)
            height = int(size.find('height').text)

            yolo_lines = []
            for obj in root.findall('object'):
                name_node = obj.find('name')
                if name_node is None or name_node.text not in self._class_map:
                    continue
                
                cls_id = self._class_map[name_node.text]
                bndbox = obj.find('bndbox')
                if bndbox is None: continue
                
                box = (
                    float(bndbox.find('xmin').text),
                    float(bndbox.find('xmax').text),
                    float(bndbox.find('ymin').text),
                    float(bndbox.find('ymax').text)
                )
                
                bb = self._convert_bbox((width, height), box)
                yolo_lines.append(f"{cls_id} {bb[0]:.6f} {bb[1]:.6f} {bb[2]:.6f} {bb[3]:.6f}")

            if yolo_lines:
                shutil.copy2(img_file, img_dest / img_file.name)
                with open(lbl_dest / xml_file.with_suffix('.txt').name, 'w') as f:
                    f.write('\n'.join(yolo_lines))
                    
        except Exception as e:
            logger.error(f"Error processing {xml_file}: {e}")

    def create_data_yaml(self) -> None:
        """Generates the data.yaml file."""
        content = {
            'train': str(self.dirs['train_img'].resolve()),
            'val': str(self.dirs['val_img'].resolve()),
            'nc': len(self.classes),
            'names': self.classes
        }
        with open(self.output_dir / 'data.yaml', 'w') as f:
            yaml.dump(content, f, default_flow_style=False)

    def process(self, test_size: float = 0.2) -> None:
        """Main execution method."""
        self._setup_directories()
        xml_files = list(self.source_dir.glob('*.xml'))
        
        if not xml_files:
            logger.error("No XML files found.")
            return

        self._extract_classes(xml_files)
        train_files, val_files = self._stratified_split(xml_files, test_size)

        logger.info(f"Processing {len(train_files)} training files...")
        for f in tqdm(train_files, desc="Processing Train", unit="file"):
            self._process_file(f, self.dirs['train_img'], self.dirs['train_lbl'])
        
        logger.info(f"Processing {len(val_files)} validation files...")
        for f in tqdm(val_files, desc="Processing Val", unit="file"):
            self._process_file(f, self.dirs['val_img'], self.dirs['val_lbl'])

        self.create_data_yaml()
        logger.info("Data preparation completed.")
