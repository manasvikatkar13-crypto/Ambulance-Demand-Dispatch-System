import os
import numpy as np
import pandas as pd

def generate_triage_dataset(num_samples: int = 5000, random_seed: int = 42, noise_rate: float = 0.035) -> pd.DataFrame:
    """
    Generates a realistic synthetic patient triage dataset based on clinical emergency vitals:
      - age: 1 to 90
      - heart_rate: 30 to 180 bpm
      - systolic_bp: 60 to 230 mmHg
      - respiratory_rate: 8 to 40 breaths/min
      - spo2: 70% to 100%
      - gcs: 3 to 15 (Glasgow Coma Scale)

    Severity Clinical Criteria:
      - Critical: SpO2 < 90% OR GCS <= 8 OR Systolic BP < 85 or > 190 OR Heart Rate < 45 or > 135
      - Moderate: SpO2 90–94% OR GCS 9–13 OR Systolic BP 85–100 or 151–180 OR Heart Rate 106–135 OR Age > 70
      - Minor: Stable vitals outside the above thresholds

    Includes both multi-organ failure and isolated single-vital clinical presentations
    (e.g., isolated head trauma GCS <= 8, isolated arrhythmia, isolated hypoxia).
    A small noise margin (~3-4%) is applied to simulate clinical edge-case variability.
    """
    np.random.seed(random_seed)

    records = []

    # Baseline healthy generator
    def baseline_vitals():
        return {
            'age': int(np.random.randint(18, 65)),
            'heart_rate': int(np.clip(np.random.normal(75, 8), 55, 100)),
            'systolic_bp': int(np.clip(np.random.normal(120, 8), 105, 140)),
            'respiratory_rate': int(np.clip(np.random.normal(16, 2), 12, 20)),
            'spo2': int(np.clip(np.random.normal(98, 1), 95, 100)),
            'gcs': int(np.random.choice([14, 15], p=[0.05, 0.95]))
        }

    # 1. Generate Minor cases (~1600)
    for _ in range(1600):
        v = baseline_vitals()
        records.append(v)

    # 2. Generate Moderate cases (~1700)
    mod_types = ['age_elderly', 'hypoxia_mild', 'ams_moderate', 'bp_low_mod', 'bp_high_mod', 'tachy_mod', 'multi_mod']
    for _ in range(1700):
        v = baseline_vitals()
        t = np.random.choice(mod_types)
        if t == 'age_elderly':
            v['age'] = int(np.random.randint(71, 91))
        elif t == 'hypoxia_mild':
            v['spo2'] = int(np.random.randint(90, 95))
        elif t == 'ams_moderate':
            v['gcs'] = int(np.random.randint(9, 14))
        elif t == 'bp_low_mod':
            v['systolic_bp'] = int(np.random.randint(85, 101))
        elif t == 'bp_high_mod':
            v['systolic_bp'] = int(np.random.randint(151, 181))
        elif t == 'tachy_mod':
            v['heart_rate'] = int(np.random.randint(106, 136))
        elif t == 'multi_mod':
            v['age'] = int(np.random.randint(65, 80))
            v['heart_rate'] = int(np.random.randint(100, 125))
            v['spo2'] = int(np.random.randint(91, 95))
            v['respiratory_rate'] = int(np.random.randint(20, 26))
        records.append(v)

    # 3. Generate Critical cases (~1700)
    crit_types = [
        'hypoxia_severe', 'coma_gcs', 'shock_hypotension',
        'hypertension_crisis', 'tachy_extreme', 'brady_extreme',
        'multi_critical'
    ]
    for _ in range(1700):
        v = baseline_vitals()
        t = np.random.choice(crit_types)
        if t == 'hypoxia_severe':
            v['spo2'] = int(np.random.randint(70, 90))
            v['respiratory_rate'] = int(np.random.randint(24, 38))
        elif t == 'coma_gcs':
            v['gcs'] = int(np.random.randint(3, 9))
        elif t == 'shock_hypotension':
            v['systolic_bp'] = int(np.random.randint(55, 85))
            v['heart_rate'] = int(np.random.randint(90, 140))
        elif t == 'hypertension_crisis':
            v['systolic_bp'] = int(np.random.randint(191, 235))
        elif t == 'tachy_extreme':
            v['heart_rate'] = int(np.random.randint(136, 180))
        elif t == 'brady_extreme':
            v['heart_rate'] = int(np.random.randint(30, 45))
        elif t == 'multi_critical':
            v['spo2'] = int(np.random.randint(75, 89))
            v['gcs'] = int(np.random.randint(3, 8))
            v['systolic_bp'] = int(np.random.choice([np.random.randint(60, 84), np.random.randint(192, 220)]))
            v['heart_rate'] = int(np.random.choice([np.random.randint(35, 44), np.random.randint(137, 165)]))
        records.append(v)

    df = pd.DataFrame(records)

    # If length exceeds 5000, sample down to 5000
    if len(df) > num_samples:
        df = df.sample(n=num_samples, random_state=random_seed).reset_index(drop=True)

    # Assign Ground Truth Clinical Severity based on established criteria:
    def evaluate_severity(row):
        # Critical criteria
        if (row['spo2'] < 90 or 
            row['gcs'] <= 8 or 
            row['systolic_bp'] < 85 or row['systolic_bp'] > 190 or 
            row['heart_rate'] < 45 or row['heart_rate'] > 135):
            return "Critical"
        # Moderate criteria
        elif (90 <= row['spo2'] <= 94 or 
              9 <= row['gcs'] <= 13 or 
              (85 <= row['systolic_bp'] <= 100) or (151 <= row['systolic_bp'] <= 180) or 
              (106 <= row['heart_rate'] <= 135) or 
              row['age'] > 70):
            return "Moderate"
        else:
            return "Minor"

    df['severity'] = df.apply(evaluate_severity, axis=1)

    # Inject realistic noise margin (~3.5%) to avoid trivial 100% and mirror real clinical edge-cases
    num_noisy = int(len(df) * noise_rate)
    noise_indices = np.random.choice(df.index, size=num_noisy, replace=False)
    classes = ["Critical", "Moderate", "Minor"]

    for idx in noise_indices:
        current_sev = df.loc[idx, 'severity']
        possible_alts = [c for c in classes if c != current_sev]
        df.loc[idx, 'severity'] = np.random.choice(possible_alts)

    # Final shuffle
    df = df.sample(frac=1.0, random_state=random_seed).reset_index(drop=True)
    return df

if __name__ == "__main__":
    os.makedirs('data', exist_ok=True)
    df_triage = generate_triage_dataset(num_samples=5000, random_seed=42, noise_rate=0.035)
    output_path = os.path.join('data', 'triage_records.csv')
    df_triage.to_csv(output_path, index=False)
    print(f"Generated {len(df_triage)} triage records saved to {output_path}")
    print("\nClass distribution:")
    print(df_triage['severity'].value_counts())
    print("\nSample records:")
    print(df_triage.head())
