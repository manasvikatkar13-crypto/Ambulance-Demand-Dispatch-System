import os
import sys

# Ensure root directory is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import joblib
import pandas as pd
import pytest
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

MODEL_PATH = os.path.join("models", "triage_classifier.joblib")
DATA_PATH = os.path.join("data", "triage_records.csv")

def test_model_artifact_exists():
    """Verify that the trained model artifact and dataset exist."""
    assert os.path.exists(MODEL_PATH), f"Model file not found at {MODEL_PATH}"
    assert os.path.exists(DATA_PATH), f"Data file not found at {DATA_PATH}"

def test_model_accuracy_exceeds_90_percent():
    """
    Evaluates the model on the held-out 20% test split from data/triage_records.csv.
    Verifies that the overall accuracy strictly exceeds 90%.
    """
    model = joblib.load(MODEL_PATH)
    df = pd.read_csv(DATA_PATH)
    
    feature_cols = ['age', 'heart_rate', 'systolic_bp', 'respiratory_rate', 'spo2', 'gcs']
    X = df[feature_cols]
    y = df['severity']
    
    _, X_test, _, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"\n[Test] Evaluated Test Accuracy: {accuracy * 100:.2f}%")
    assert accuracy > 0.90, f"Expected accuracy > 0.90, but got {accuracy:.4f}"

def test_critical_patient_mapping():
    """
    Tests severe, acute clinical presentations across each vital sign threshold
    to ensure the model robustly maps them to 'Critical'.
    """
    model = joblib.load(MODEL_PATH)

    critical_scenarios = [
        # 1. Hypoxemia (SpO2 < 90%)
        {"name": "Severe Hypoxia", "age": 45, "heart_rate": 80, "systolic_bp": 120, "respiratory_rate": 20, "spo2": 82, "gcs": 15},
        # 2. Coma / Severe Neurological Impairment (GCS <= 8)
        {"name": "Coma / GCS 5", "age": 30, "heart_rate": 78, "systolic_bp": 122, "respiratory_rate": 14, "spo2": 98, "gcs": 5},
        # 3. Severe Hypotension / Circulatory Shock (Systolic BP < 85)
        {"name": "Shock / Hypotension", "age": 50, "heart_rate": 92, "systolic_bp": 72, "respiratory_rate": 16, "spo2": 97, "gcs": 14},
        # 4. Hypertensive Crisis (Systolic BP > 190)
        {"name": "Severe Hypertension", "age": 62, "heart_rate": 88, "systolic_bp": 210, "respiratory_rate": 18, "spo2": 96, "gcs": 15},
        # 5. Extreme Tachycardia (Heart Rate > 135)
        {"name": "Extreme Tachycardia", "age": 38, "heart_rate": 152, "systolic_bp": 124, "respiratory_rate": 22, "spo2": 97, "gcs": 15},
        # 6. Extreme Bradycardia (Heart Rate < 45)
        {"name": "Extreme Bradycardia", "age": 55, "heart_rate": 36, "systolic_bp": 118, "respiratory_rate": 14, "spo2": 98, "gcs": 15},
    ]

    for scenario in critical_scenarios:
        df_case = pd.DataFrame([{
            'age': scenario['age'],
            'heart_rate': scenario['heart_rate'],
            'systolic_bp': scenario['systolic_bp'],
            'respiratory_rate': scenario['respiratory_rate'],
            'spo2': scenario['spo2'],
            'gcs': scenario['gcs']
        }])
        pred = model.predict(df_case)[0]
        assert pred == "Critical", f"Scenario '{scenario['name']}' failed! Expected 'Critical' but got '{pred}'"

def test_api_predict_valid_inputs():
    """
    Tests POST /triage/predict with valid payloads representing
    Critical, Moderate, and Minor patients.
    """
    # 1. Critical test case
    crit_payload = {
        "age": 65,
        "heart_rate": 148.0,
        "systolic_bp": 74.0,
        "respiratory_rate": 30.0,
        "spo2": 84.0,
        "gcs": 6
    }
    res_crit = client.post("/triage/predict", json=crit_payload)
    assert res_crit.status_code == 200, res_crit.text
    data_crit = res_crit.json()
    assert data_crit["severity"] == "Critical"
    assert "Critical" in data_crit["probabilities"]
    assert data_crit["probabilities"]["Critical"] > 0.50
    assert "Code 3" in data_crit["recommended_action"]

    # 2. Moderate test case
    mod_payload = {
        "age": 78,
        "heart_rate": 118.0,
        "systolic_bp": 162.0,
        "respiratory_rate": 22.0,
        "spo2": 92.0,
        "gcs": 12
    }
    res_mod = client.post("/triage/predict", json=mod_payload)
    assert res_mod.status_code == 200, res_mod.text
    data_mod = res_mod.json()
    assert data_mod["severity"] == "Moderate"
    assert "Code 2" in data_mod["recommended_action"]

    # 3. Minor test case
    minor_payload = {
        "age": 25,
        "heart_rate": 72.0,
        "systolic_bp": 118.0,
        "respiratory_rate": 16.0,
        "spo2": 99.0,
        "gcs": 15
    }
    res_minor = client.post("/triage/predict", json=minor_payload)
    assert res_minor.status_code == 200, res_minor.text
    data_minor = res_minor.json()
    assert data_minor["severity"] == "Minor"
    assert "Code 1" in data_minor["recommended_action"]

def test_api_predict_invalid_inputs():
    """
    Tests input validation on POST /triage/predict, ensuring
    out-of-range clinical parameters and missing fields return HTTP 422.
    """
    # Invalid GCS (greater than 15)
    res_gcs_high = client.post("/triage/predict", json={
        "age": 30, "heart_rate": 80, "systolic_bp": 120, "respiratory_rate": 16, "spo2": 98, "gcs": 20
    })
    assert res_gcs_high.status_code == 422

    # Invalid GCS (less than 3)
    res_gcs_low = client.post("/triage/predict", json={
        "age": 30, "heart_rate": 80, "systolic_bp": 120, "respiratory_rate": 16, "spo2": 98, "gcs": 1
    })
    assert res_gcs_low.status_code == 422

    # Invalid SpO2 (> 100%)
    res_spo2_high = client.post("/triage/predict", json={
        "age": 30, "heart_rate": 80, "systolic_bp": 120, "respiratory_rate": 16, "spo2": 105, "gcs": 15
    })
    assert res_spo2_high.status_code == 422

    # Negative age
    res_age_neg = client.post("/triage/predict", json={
        "age": -5, "heart_rate": 80, "systolic_bp": 120, "respiratory_rate": 16, "spo2": 98, "gcs": 15
    })
    assert res_age_neg.status_code == 422

    # Empty payload
    res_empty = client.post("/triage/predict", json={})
    assert res_empty.status_code == 422
