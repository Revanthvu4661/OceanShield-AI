# OceanShield AI

Intelligent rogue wave risk assessment for maritime navigation.

## Quick Start

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend
Open `frontend/index.html` directly, or let FastAPI serve it at `http://localhost:8000`.

## API Reference

- `POST /api/predict` - Submit ocean conditions, get risk score
- `GET /api/history` - Last 20 predictions
- `GET /api/explain/{id}` - Full explanation for a prediction
- `POST /api/ai-search` - Gemini-powered maritime research
- `GET /api/health` - Model status and performance metrics

### Gemini Setup
Get a free API key from [Google AI Studio](https://aistudio.google.com), then enter it in the AI Research panel.

## Model Details

- Algorithm: XGBoost (71 features)
- Accuracy: 99.27%
- F1: 95.00%
- ROC-AUC: 99.92%
- Training data: Beach hourly ocean forecasts (chronological split)
- Label: `rogue_risk_label` proxy

## Docker

```bash
docker compose up --build
```

The app will be available at `http://localhost:8000`.

## Render Deployment

Use the root `Dockerfile` and set the service to listen on the platform-provided `PORT` environment variable. Render will automatically provide `PORT` for the web service.
