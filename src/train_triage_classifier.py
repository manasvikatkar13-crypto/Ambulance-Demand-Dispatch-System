import os
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

def train_triage_model(
    data_path: str = 'data/triage_records.csv',
    model_save_path: str = 'models/triage_classifier.joblib'
):
    print(f"Loading triage records from {data_path}...")
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Dataset not found at {data_path}. Run generate_triage_data.py first.")

    df = pd.read_csv(data_path)
    feature_cols = ['age', 'heart_rate', 'systolic_bp', 'respiratory_rate', 'spo2', 'gcs']
    target_col = 'severity'

    X = df[feature_cols]
    y = df[target_col]

    # Stratified 80/20 train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    print(f"Dataset split: Train={len(X_train)} samples, Test={len(X_test)} samples")

    # Build Pipeline with RandomForestClassifier
    pipeline = Pipeline([
        ('classifier', RandomForestClassifier(
            n_estimators=150,
            max_depth=14,
            min_samples_split=4,
            random_state=42
        ))
    ])

    print("Training RandomForest triage classifier...")
    pipeline.fit(X_train, y_train)

    # Evaluate on held-out test set
    y_pred = pipeline.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred, labels=['Critical', 'Moderate', 'Minor'])
    cr = classification_report(y_test, y_pred, labels=['Critical', 'Moderate', 'Minor'], digits=4)

    print("\n================ EVALUATION METRICS ================")
    print(f"Overall Accuracy: {acc * 100:.2f}% (Target: >90%)")
    print("\nClassification Report:")
    print(cr)
    print("Confusion Matrix (Labels: ['Critical', 'Moderate', 'Minor']):")
    print(cm)
    print("====================================================\n")

    if acc < 0.90:
        raise ValueError(f"Accuracy {acc*100:.2f}% did not meet the >90% requirement!")

    os.makedirs(os.path.dirname(model_save_path), exist_ok=True)
    joblib.dump(pipeline, model_save_path)
    print(f"Trained pipeline successfully saved to {model_save_path}")

    return pipeline, acc

if __name__ == "__main__":
    train_triage_model()
