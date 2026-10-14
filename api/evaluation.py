"""
AI-Based Emergency Ambulance Demand & Dispatch System
ML Model Evaluation Engine (Step 17)

This module loads, structures, and serves the empirical model evaluation results
generated during Step 8.5 comparative experiments. It parses 'reports/classifier_comparison.csv'
and provides structured metrics, confusion matrices, and transparent decision-support
context for the React dashboard.

MODELS COMPARED:
1. Majority-Class Baseline (heuristic predicting NORMAL 100% of the time)
2. K-Nearest Neighbors (k=5, Distance-Weighted on balanced training data)
3. Class-Weighted Random Forest (Selected Candidate Pipeline)
4. Class-Weighted HistGradientBoosting (Gradient Boosting on Decision Trees)

All models were evaluated on the identical chronological test set (N=5,000, cutoff: 2019-08-26).
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

class ConfusionMatrixData(BaseModel):
    tp: int = Field(..., description="True Positives: Correctly anticipated HIGH surges (>= 2 calls)")
    fn: int = Field(..., description="False Negatives: Missed HIGH surges (predicted NORMAL)")
    fp: int = Field(..., description="False Positives: False alarms (predicted HIGH, actual NORMAL)")
    tn: int = Field(..., description="True Negatives: Correctly anticipated NORMAL operations (< 2 calls)")
    total_samples: int = Field(..., description="Total test samples evaluated (TP + FN + FP + TN)")
    actual_high: int = Field(..., description="Total actual HIGH demand occurrences (TP + FN)")
    actual_normal: int = Field(..., description="Total actual NORMAL demand occurrences (FP + TN)")
    predicted_high: int = Field(..., description="Total times model predicted HIGH (TP + FP)")
    predicted_normal: int = Field(..., description="Total times model predicted NORMAL (TN + FN)")
    cell_explanations: Dict[str, str] = Field(..., description="Plain-language operational meaning of each quadrant")


class ModelMetricsItem(BaseModel):
    model_id: str = Field(..., description="Unique machine-readable model identifier")
    model_name: str = Field(..., description="Formal model display name")
    architecture_type: str = Field(..., description="Machine learning family / architecture")
    is_selected_candidate: bool = Field(..., description="True if selected as candidate dispatch pipeline")
    overall_accuracy: float = Field(..., description="Raw overall accuracy (can be deceptive under imbalance)")
    balanced_accuracy: float = Field(..., description="Unweighted average of recall across both classes")
    high_precision: float = Field(..., description="Positive Predictive Value for HIGH class: TP / (TP + FP)")
    high_recall: float = Field(..., description="Sensitivity for HIGH class: TP / (TP + FN)")
    high_f1_score: float = Field(..., description="Harmonic mean of precision and recall for HIGH class")
    train_time_seconds: float = Field(..., description="Model fitting time in seconds")
    predicted_high_count: int = Field(..., description="Count of HIGH alerts triggered in test sample")
    confusion_matrix: ConfusionMatrixData = Field(..., description="Exact 2x2 confusion matrix counts and labels")
    strengths: List[str] = Field(..., description="Key algorithmic strengths observed in evaluation")
    weaknesses: List[str] = Field(..., description="Key operational weaknesses observed in evaluation")
    operational_assessment: str = Field(..., description="Summary operational assessment for EMS dispatch")


class EvaluationMetadata(BaseModel):
    train_cutoff_date: str = Field(..., description="Chronological cutoff dividing train from test data")
    test_start_date: str = Field(..., description="Earliest date evaluated in the test sample")
    test_sample_size: int = Field(..., description="Exact sample count in test dataset (N=5,000)")
    test_high_count: int = Field(..., description="Actual HIGH events in test sample (73)")
    test_normal_count: int = Field(..., description="Actual NORMAL events in test sample (4,927)")
    test_high_prevalence_pct: float = Field(..., description="Prevalence percentage of HIGH events in test set (1.46%)")
    train_sample_size: int = Field(..., description="Balanced training set sample size (40,000)")
    feature_list: List[str] = Field(..., description="10 input features used by all ML models")
    target_definition: str = Field(..., description="Operational definition of HIGH (>= 2 calls) vs NORMAL (< 2 calls)")
    sampling_procedure: str = Field(..., description="Sampling methodology enforcing naturally imbalanced test evaluation")
    report_source: str = Field(..., description="Relative report file path originating the data")


class EvaluationEducationalGuidance(BaseModel):
    why_accuracy_is_misleading: str = Field(..., description="Explanation of why raw accuracy fails on imbalanced emergency data")
    operational_tradeoffs: str = Field(..., description="Analysis of false alarms vs missed surges in ambulance logistics")
    academic_prototype_disclaimer: str = Field(..., description="Explicit disclaimer clarifying academic decision-support scope")


class ModelEvaluationResponse(BaseModel):
    models: List[ModelMetricsItem] = Field(..., description="List of all 4 evaluated model architectures")
    metadata: EvaluationMetadata = Field(..., description="Experimental protocol and dataset metadata")
    guidance: EvaluationEducationalGuidance = Field(..., description="Educational context on trade-offs and metrics")
    selected_model_id: str = Field(..., description="ID of the model selected for deployment (random_forest)")
    disclaimer: str = Field(..., description="Mandatory academic prototype disclaimer")


# ---------------------------------------------------------------------------
# Static Fallback Data (verbatim from reports/classifier_comparison.csv)
# ---------------------------------------------------------------------------
VERIFIED_HISTORICAL_RESULTS = [
    {
        "model_id": "majority_baseline",
        "model_name": "Majority-Class Baseline",
        "architecture_type": "Zero-Rule Heuristic",
        "is_selected_candidate": False,
        "overall_accuracy": 0.9854,
        "balanced_accuracy": 0.5000,
        "high_precision": 0.0000,
        "high_recall": 0.0000,
        "high_f1_score": 0.0000,
        "tp": 0,
        "fn": 73,
        "fp": 0,
        "tn": 4927,
        "predicted_high_count": 0,
        "train_time_seconds": 0.0,
        "strengths": [
            "Shows 98.54% overall accuracy purely by predicting the majority class.",
            "Requires zero computational resources or training time.",
            "Illustrates the severe deception of raw accuracy on imbalanced data."
        ],
        "weaknesses": [
            "Misses 100% of emergency surges (0 of 73 caught; 0% recall).",
            "Zero operational utility for emergency dispatch planning.",
            "Provides no decision support capability whatsoever."
        ],
        "operational_assessment": "Unusable for dispatch. Demonstrates the 'accuracy paradox': a model that fails all emergencies can still boast a 98.54% raw accuracy score."
    },
    {
        "model_id": "knn",
        "model_name": "KNN (k=5, Distance-Weighted)",
        "architecture_type": "Instance-Based Non-Parametric",
        "is_selected_candidate": False,
        "overall_accuracy": 0.5732,
        "balanced_accuracy": 0.6822,
        "high_precision": 0.0266,
        "high_recall": 0.7945,
        "high_f1_score": 0.0516,
        "tp": 58,
        "fn": 15,
        "fp": 2119,
        "tn": 2808,
        "predicted_high_count": 2177,
        "train_time_seconds": 0.12,
        "strengths": [
            "High minority surge recall (79.45%), catching 58 of 73 surges.",
            "Fast training time (0.12s) on balanced sample.",
            "Simple, non-parametric distance-based classification."
        ],
        "weaknesses": [
            "Severe false alarm rate: 2,119 false positives (only 2.66% precision).",
            "Curse of dimensionality in one-hot encoded township space causes distance distortion.",
            "Triggers HIGH alert in 43.5% of all evaluated hours, causing catastrophic alarm fatigue."
        ],
        "operational_assessment": "Excessive false alarms would overwhelm dispatch supervisors and exhaust fleet reserves staging vehicles for non-existent surges."
    },
    {
        "model_id": "random_forest",
        "model_name": "Random Forest (Class-Weighted)",
        "architecture_type": "Bagged Decision Tree Ensemble",
        "is_selected_candidate": True,
        "overall_accuracy": 0.9014,
        "balanced_accuracy": 0.7745,
        "high_precision": 0.0914,
        "high_recall": 0.6438,
        "high_f1_score": 0.1601,
        "tp": 47,
        "fn": 26,
        "fp": 467,
        "tn": 4460,
        "predicted_high_count": 514,
        "train_time_seconds": 2.06,
        "strengths": [
            "Highest F1-Score (16.01%) among all evaluated candidates.",
            "Cuts false alarms by over 77.9% compared to KNN (from 2,119 down to 467).",
            "Maintains 90.14% overall accuracy while preserving 64.38% surge recall (47 of 73 caught).",
            "Robust against high-dimensional one-hot encoded categorical features."
        ],
        "weaknesses": [
            "Misses 26 actual surges (35.6% false negative rate).",
            "Precision is 9.14% (roughly 1 in 11 alerts is an actual surge).",
            "Higher training latency (2.06s) than KNN, though still modest."
        ],
        "operational_assessment": "Selected as candidate production model. Provides the most balanced operational compromise between catching critical surges and preventing dispatcher alarm fatigue."
    },
    {
        "model_id": "hist_gradient_boosting",
        "model_name": "HistGradientBoosting (Class-Weighted)",
        "architecture_type": "Histogram-Based Gradient Boosting",
        "is_selected_candidate": False,
        "overall_accuracy": 0.7668,
        "balanced_accuracy": 0.8007,
        "high_precision": 0.0502,
        "high_recall": 0.8356,
        "high_f1_score": 0.0947,
        "tp": 61,
        "fn": 12,
        "fp": 1154,
        "tn": 3773,
        "predicted_high_count": 1215,
        "train_time_seconds": 2.42,
        "strengths": [
            "Highest Recall (83.56%), missing only 12 out of 73 emergency surges.",
            "Highest Balanced Accuracy (80.07%) across both demand classes.",
            "Effective non-linear gradient-boosted decision trees."
        ],
        "weaknesses": [
            "High false alarm count (1,154 false positives; 5.02% precision).",
            "More than double the false positives of Random Forest.",
            "Lower F1-Score (9.47%) due to excessive false alarms."
        ],
        "operational_assessment": "Strong alternative if dispatch priority is strictly minimizing missed surges at the expense of accepting 1,154 false alarms. Outranked by Random Forest on alarm efficiency."
    }
]


CELL_EXPLANATIONS = {
    "tp": "True Positive: Model correctly alerted to a HIGH surge (>= 2 calls), and an actual surge occurred. Dispatchers successfully staged reserve units in advance.",
    "fn": "False Negative (Missed Surge): Model predicted NORMAL demand, but an actual HIGH surge (>= 2 calls) occurred. Response times may lengthen as no reserve units were staged.",
    "fp": "False Positive (False Alarm): Model alerted to a HIGH surge, but demand remained NORMAL (< 2 calls). Ambulances were staged unnecessarily, increasing crew wear and dispatcher alarm fatigue.",
    "tn": "True Negative: Model predicted NORMAL demand (< 2 calls), and operations remained NORMAL. Standard station patrol postures were maintained without unnecessary vehicle relocation."
}


# ---------------------------------------------------------------------------
# Data Loader Logic
# ---------------------------------------------------------------------------

def _load_csv_metrics() -> List[Dict[str, Any]]:
    """
    Attempts to read actual metrics from reports/classifier_comparison.csv.
    Falls back gracefully to the verified historical numbers if the CSV is missing.
    """
    csv_path = Path("reports/classifier_comparison.csv")
    if not csv_path.exists():
        # Fall back to root or parent search
        alt_path = Path(__file__).resolve().parent.parent / "reports" / "classifier_comparison.csv"
        if alt_path.exists():
            csv_path = alt_path

    if csv_path.exists():
        try:
            df = pd.read_csv(csv_path)
            # Map rows to our structured items
            results = []
            for item in VERIFIED_HISTORICAL_RESULTS:
                # Find matching row in df by substring match on model name
                name = item["model_name"]
                match = df[df["Model"].str.contains(name.split()[0], case=False, na=False)]
                if not match.empty:
                    row = match.iloc[0]
                    updated = dict(item)
                    updated["overall_accuracy"] = round(float(row.get("Overall Accuracy", item["overall_accuracy"])), 4)
                    updated["balanced_accuracy"] = round(float(row.get("Balanced Accuracy", item["balanced_accuracy"])), 4)
                    updated["high_precision"] = round(float(row.get("HIGH Precision", item["high_precision"])), 4)
                    updated["high_recall"] = round(float(row.get("HIGH Recall", item["high_recall"])), 4)
                    updated["high_f1_score"] = round(float(row.get("HIGH F1-Score", item["high_f1_score"])), 4)
                    updated["tp"] = int(row.get("True Positives (TP)", item["tp"]))
                    updated["fn"] = int(row.get("False Negatives (FN)", item["fn"]))
                    updated["fp"] = int(row.get("False Positives (FP)", item["fp"]))
                    updated["tn"] = int(row.get("True Negatives (TN)", item["tn"]))
                    updated["predicted_high_count"] = int(row.get("Predicted HIGH Count", item["predicted_high_count"]))
                    updated["train_time_seconds"] = round(float(row.get("Train Time (s)", item["train_time_seconds"])), 2)
                    results.append(updated)
                else:
                    results.append(item)
            return results
        except Exception:
            return VERIFIED_HISTORICAL_RESULTS

    return VERIFIED_HISTORICAL_RESULTS


def get_model_evaluations() -> ModelEvaluationResponse:
    """
    Assembles complete model evaluation data, confusion matrices, and educational guidance.
    """
    raw_models = _load_csv_metrics()

    items: List[ModelMetricsItem] = []
    for raw in raw_models:
        tp = raw["tp"]
        fn = raw["fn"]
        fp = raw["fp"]
        tn = raw["tn"]

        cm = ConfusionMatrixData(
            tp=tp,
            fn=fn,
            fp=fp,
            tn=tn,
            total_samples=tp + fn + fp + tn,
            actual_high=tp + fn,
            actual_normal=fp + tn,
            predicted_high=tp + fp,
            predicted_normal=tn + fn,
            cell_explanations=CELL_EXPLANATIONS,
        )

        items.append(
            ModelMetricsItem(
                model_id=raw["model_id"],
                model_name=raw["model_name"],
                architecture_type=raw["architecture_type"],
                is_selected_candidate=raw["is_selected_candidate"],
                overall_accuracy=raw["overall_accuracy"],
                balanced_accuracy=raw["balanced_accuracy"],
                high_precision=raw["high_precision"],
                high_recall=raw["high_recall"],
                high_f1_score=raw["high_f1_score"],
                train_time_seconds=raw["train_time_seconds"],
                predicted_high_count=raw["predicted_high_count"],
                confusion_matrix=cm,
                strengths=raw["strengths"],
                weaknesses=raw["weaknesses"],
                operational_assessment=raw["operational_assessment"],
            )
        )

    metadata = EvaluationMetadata(
        train_cutoff_date="Train through 2019-08-25",
        test_start_date="Test from 2019-08-26 onward",
        test_sample_size=5000,
        test_high_count=73,
        test_normal_count=4927,
        test_high_prevalence_pct=1.46,
        train_sample_size=40000,
        feature_list=[
            "twp", "hour", "month", "day_of_week", "is_weekend",
            "temperature_2m", "relative_humidity_2m", "precipitation",
            "wind_speed_10m", "weather_code"
        ],
        target_definition="HIGH demand (>= 2 calls in zone-hour) vs NORMAL demand (< 2 calls)",
        sampling_procedure="Chronological split: training through 2019-08-25 (balanced 20k HIGH + 20k NORMAL); test from 2019-08-26 (naturally imbalanced 5,000 samples, 1.46% HIGH base rate).",
        report_source="reports/classifier_comparison.csv",
    )

    guidance = EvaluationEducationalGuidance(
        why_accuracy_is_misleading=(
            "In emergency call datasets, critical demand surges are relatively rare (only 1.46% in our test set). "
            "A naive 'Majority-Class Baseline' that constantly predicts NORMAL achieves 98.54% overall accuracy purely by "
            "ignoring the minority class. However, it catches 0 out of 73 actual emergencies (0% recall), making it "
            "completely useless for dispatch. Raw accuracy treats every prediction equally, masking catastrophic failure "
            "on the rare minority class where patient lives are at stake."
        ),
        operational_tradeoffs=(
            "Emergency dispatch faces an unavoidable operational trade-off between sensitivity and specificity: "
            "(1) Missed Surges (False Negatives): If a surge is missed, reserve ambulances remain stationed at central depots, "
            "leading to delayed response times during life-threatening calls. "
            "(2) False Alarms (False Positives): If the system over-predicts surges, reserve ambulances are staged unnecessarily, "
            "wasting fuel, exhausting paramedics, and causing 'alarm fatigue'—if dispatchers find that 90%+ of alerts are false alarms, "
            "they will ignore the tool. "
            "Random Forest was chosen as candidate because it cut false alarms by 77.9% compared to KNN (467 vs 2,119) while "
            "retaining a solid 64.38% surge recall (catching 47 of 73 surges)."
        ),
        academic_prototype_disclaimer=(
            "Even for the top-performing Random Forest model, HIGH-class precision is 9.14% (meaning roughly 1 in 11 alerts corresponds "
            "to an actual surge). In live emergency healthcare operations, autonomous dispatch requires far higher precision. "
            "Therefore, this model serves as an academic decision-support prototype to inform human supervisory staffing rather "
            "than an autonomous dispatch replacement for 911 telecommunicators."
        )
    )

    disclaimer = (
        "Academic ML Capstone Evaluation: Metrics were computed on a retrospective, chronological test sample "
        "(5,000 records from Montgomery County EMS historical data, 2019-08-26 onward). These historical evaluation "
        "metrics reflect retrospective model discrimination and do not constitute a clinical guarantee or operational "
        "dispatch certification."
    )

    return ModelEvaluationResponse(
        models=items,
        metadata=metadata,
        guidance=guidance,
        selected_model_id="random_forest",
        disclaimer=disclaimer,
    )


def get_single_model_evaluation(model_id: str) -> Optional[ModelMetricsItem]:
    """
    Returns evaluation metrics for a specific model by ID, or None if not found.
    """
    resp = get_model_evaluations()
    for m in resp.models:
        if m.model_id == model_id:
            return m
    return None
