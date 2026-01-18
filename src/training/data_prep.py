import logging
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
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
        logger.info(f"Classes found: {self.classes}")

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
        train_files, val_files = train_test_split(xml_files, test_size=test_size, random_state=42)

        logger.info(f"Processing {len(train_files)} training files...")
        for f in tqdm(train_files, desc="Processing Train", unit="file"):
            self._process_file(f, self.dirs['train_img'], self.dirs['train_lbl'])
        
        logger.info(f"Processing {len(val_files)} validation files...")
        for f in tqdm(val_files, desc="Processing Val", unit="file"):
            self._process_file(f, self.dirs['val_img'], self.dirs['val_lbl'])

        self.create_data_yaml()
        logger.info("Data preparation completed.")
