# STRIDE-YOLO: Automated Threat Modeling with AI

[![Python](https://img.shields.io/badge/Python-3.10-blue.svg)](https://www.python.org/)
[![YOLO](https://img.shields.io/badge/YOLO-v8-orange.svg)](https://ultralytics.com/)
[![Docker](https://img.shields.io/badge/Docker-GPU%20%7C%20CPU-green.svg)](https://www.docker.com/)

An AI-powered tool that automatically performs **STRIDE threat modeling** by analyzing software architecture diagrams. Developed as an MVP for FIAP Software Security to validate the feasibility of automated vulnerability analysis in system architectures.

## Overview

This application uses a **YOLOv8** object detection model trained to identify cloud infrastructure components (AWS, Azure, GCP) in architecture diagrams. Once detected, each component is mapped to potential security threats using the **STRIDE methodology**:

| STRIDE | Threat Type | Description |
|--------|-------------|-------------|
| **S** | Spoofing | Impersonating users or systems |
| **T** | Tampering | Modifying data or code maliciously |
| **R** | Repudiation | Denying actions without audit trail |
| **I** | Information Disclosure | Exposing sensitive data |
| **D** | Denial of Service | Making services unavailable |
| **E** | Elevation of Privilege | Gaining unauthorized access |

## Features

- 🔍 **Automatic Component Detection**: Identifies 111 cloud service icons (AWS, Azure, GCP)
- 📊 **STRIDE Threat Mapping**: Maps each component to specific security threats
- 📝 **Markdown Report Generation**: Produces actionable threat model reports
- 🚀 **GPU Acceleration**: Supports NVIDIA GPUs for faster training
- 🐳 **Dockerized**: Easy deployment with CPU or GPU support

## Project Structure

```
├── dataset/
│   ├── dataset_augmented/     # Training images + XML annotations
│   └── yolo_format/           # Converted YOLO format (auto-generated)
├── models/
│   ├── train_run/             # Training artifacts and metrics
│   └── yolo_stride_v1.pt      # Trained model
├── src/
│   ├── main.py                # CLI entry point
│   ├── training/
│   │   ├── data_prep.py       # Dataset conversion (XML → YOLO)
│   │   └── train.py           # YOLO training pipeline
│   └── inference/
│       └── threat_model.py    # STRIDE threat mapping & inference
├── input_images/              # Images for inference testing
├── docker-compose.debug.yml   # CPU training/inference
├── docker-compose.gpu.yml     # GPU training/inference
├── Dockerfile                 # CPU Docker image
├── Dockerfile.gpu             # GPU Docker image (CUDA)
└── requirements.txt           # Python dependencies
```

## Requirements

- Docker & Docker Compose
- (Optional) NVIDIA GPU + [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)

## How to Run

### 1. Dataset Setup

The training dataset is **not included** in this repository. Download it from Kaggle:

📦 **[Software Architecture Dataset](https://www.kaggle.com/datasets/carlosrian/software-architecture-dataset)**

After downloading, extract and organize the files as follows:

```
dataset/
└── dataset_augmented/
    ├── aws_amazon_api_gateway_0000_aug_0.png
    ├── aws_amazon_api_gateway_0000_aug_0.xml
    ├── aws_amazon_api_gateway_0000_aug_1.png
    ├── aws_amazon_api_gateway_0000_aug_1.xml
    └── ... (all .png and .xml files)
```

> **Note**: Each image (`.png`) must have a corresponding annotation file (`.xml`) with the same name. The `yolo_format/` folder will be auto-generated during training.

### 2. Training

**With GPU (recommended):**
```bash
docker compose -f docker-compose.gpu.yml build
docker compose -f docker-compose.gpu.yml up
```

**With CPU only:**
```bash
docker compose -f docker-compose.debug.yml build
docker compose -f docker-compose.debug.yml up
```

### 3. Inference (Threat Analysis)

Place your architecture diagram in `input_images/`, then run:

```bash
# GPU
docker compose -f docker-compose.gpu.yml run --rm app \
  python src/main.py inference \
  --image /app/input_images/your_diagram.png

# CPU
docker compose -f docker-compose.debug.yml run --rm app \
  python src/main.py inference \
  --image /app/input_images/your_diagram.png
```

### Inference Options

| Flag | Default | Description |
|------|---------|-------------|
| `--image` | (required) | Path to architecture diagram |
| `--conf` | 0.15 | Confidence threshold (0.0-1.0) |
| `--imgsz` | 1280 | Inference image size |
| `--model-path` | auto | Custom model path |

### 4. Output

The report is saved as `input_images/<image_name>_report.md` with:
- Detected components
- Confidence scores
- STRIDE-based threats for each component

## Example Output

```markdown
## Component: **aws_lambda_lambda_function**
- **Confidence**: 0.85
- **Potential Threats (STRIDE)**:
  - Tampering: Malicious code injection via dependencies.
  - Denial of Service: Concurrency limit exhaustion.
  - Elevation of Privilege: Over-permissive IAM execution role.
```

## Dataset

The model was trained on the [Software Architecture Dataset](https://www.kaggle.com/datasets/carlosrian/software-architecture-dataset) from Kaggle, containing annotated cloud architecture icons.

## License

This project was developed as part of FIAP's IA para Devs course.
