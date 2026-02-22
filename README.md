# STRIDE Threat Analyzer

AI-powered cloud architecture security analysis using the **STRIDE** threat modeling methodology.

Upload a cloud architecture diagram (AWS, Azure, or GCP) and receive a comprehensive threat model report — powered by **Google Gemini**.

## How It Works

1. **Upload** your cloud architecture diagram through the web UI
2. **Gemini analyzes** the image — identifying all cloud components, data flows, and trust boundaries
3. **STRIDE report** is generated with threats and mitigations for each component

The STRIDE methodology evaluates six threat categories:
- **S**poofing — identity impersonation
- **T**ampering — data/code modification
- **R**epudiation — untraceable actions
- **I**nformation Disclosure — data exposure
- **D**enial of Service — availability attacks
- **E**levation of Privilege — unauthorized access

## Quick Start (Docker)

### Prerequisites
- Docker and Docker Compose
- A [Gemini API key](https://aistudio.google.com/apikey) (free)

### Run

```bash
# Set your Gemini API key
export GEMINI_API_KEY="your-key-here"

# Build and run
docker compose up --build
```

Then open **http://localhost:5000** in your browser.

### Development

The `src/` directory is mounted as a volume, so changes to the code are reflected without rebuilding.

To rebuild after dependency changes:

```bash
docker compose build --no-cache
docker compose up
```

## Running Without Docker

```bash
# Install dependencies
pip install -r requirements.txt

# Set your API key
export GEMINI_API_KEY="your-key-here"

# Run the development server
python src/main.py
```

## Project Structure

```
├── Dockerfile              # Container image definition
├── docker-compose.yml      # Docker Compose service config
├── requirements.txt        # Python dependencies
├── src/
│   ├── main.py             # Flask web application
│   ├── services/
│   │   └── gemini_analyzer.py  # Gemini API integration & STRIDE prompt
│   ├── templates/
│   │   └── index.html      # Web UI (upload + report display)
│   └── static/
│       └── style.css       # UI styling
└── input_images/           # Sample architecture diagrams
```

## Technology Stack

- **Backend**: Python 3.10 + Flask
- **AI**: Google Gemini 2.0 Flash (via `google-genai` SDK)
- **Container**: Docker + Docker Compose
- **Frontend**: Vanilla HTML/CSS/JS with modern dark theme
