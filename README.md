# AI-Based Emergency Ambulance Demand & Dispatch System

An AI-powered decision-support prototype that predicts emergency ambulance demand, identifies high-demand areas, and helps plan ambulance allocation and routes using historical emergency medical services (EMS) data.

## Features

- **Demand Prediction:** Estimates ambulance demand using machine learning models.
- **Hotspot Detection:** Identifies locations with historically high emergency call activity.
- **Ambulance Allocation:** Recommends ambulance distribution across zones based on predicted demand.
- **Route Planning:** Demonstrates route planning using A* search and road-routing services.
- **Integrated Dispatch:** Combines demand predictions, allocation, and route planning in one workflow.
- **Model Evaluation:** Compares classifier performance using evaluation metrics.
- **Interactive Dashboard:** Provides a React-based interface for exploring predictions and dispatch recommendations.

## Tech Stack

- **Frontend:** React, Vite, JavaScript, CSS
- **Backend:** Python, FastAPI
- **Machine Learning & Data Processing:** Pandas, NumPy, Scikit-learn, Joblib
- **Mapping & Routing:** Leaflet, OpenStreetMap, OSRM
- **Testing:** Python `unittest`

## Project Structure

- `api/` — API endpoints, allocation, dispatch, evaluation, and routing logic
- `data/` — Sample predictions, demand data, and historical hotspot information
- `frontend/` — React frontend
- `models/` — Trained machine learning models
- `reports/` — Model comparison reports and findings
- `src/` — Data preprocessing, feature engineering, and model training scripts
- `tests/` — Backend unit tests

## Getting Started

### Prerequisites

- Python 3.10 or a compatible version for the project's dependencies
- Node.js and npm

### 1. Clone the repository

```bash
git clone https://github.com/manasvikatkar13-crypto/Ambulance-Demand-Dispatch-System.git
cd Ambulance-Demand-Dispatch-System
```

### 2. Set up the Python environment

Create and activate a virtual environment:

**Windows PowerShell**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the Python dependencies after the `requirements.txt` file is added:

```powershell
pip install -r requirements.txt
```

### 3. Start the backend

From the project root, run:

```powershell
python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

The API documentation should be available at:

http://127.0.0.1:8000/docs

### 4. Start the frontend

Open a second terminal in the project root and run:

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite in your terminal, usually:

http://127.0.0.1:5173

## Dataset and Scope

This prototype uses historical EMS call data from Montgomery County, Pennsylvania, USA. It is an academic project for exploring demand prediction, hotspot analysis, ambulance allocation, and route planning.

It is **not a live emergency dispatch system**. Predictions and route recommendations should not be used for real-world emergency response without appropriate validation, operational data, and professional oversight.

## Future Improvements

- Improve prediction performance for rare high-demand periods.
- Incorporate more location-specific and recent data.
- Enhance dispatch optimization and evaluation.
- Add further testing and deployment support.

## Author

Developed as an academic machine learning and software engineering project.
