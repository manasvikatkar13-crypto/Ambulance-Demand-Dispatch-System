"""
AI-Based Emergency Ambulance Demand & Dispatch System
Step 3: Time Feature Engineering

This script loads the cleaned EMS dataset ('data/ems_cleaned.csv'),
converts the 'timeStamp' column into a datetime object, and extracts
temporal features (year, month, day, hour, day_of_week, is_weekend, date).
It also runs validation checks and prints summary distributions (calls by hour
and calls by day of the week). The output is saved to 'data/ems_features.csv'.
"""

import os
import pandas as pd


def load_cleaned_data(filepath: str) -> pd.DataFrame:
    """
    Step 1: Load the cleaned EMS dataset.
    We check if the file exists before reading it.
    """
    print(f"[INFO] Reading cleaned dataset from '{filepath}'...")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Cleaned dataset not found at: {filepath}")
    
    df = pd.read_csv(filepath)
    print(f"[INFO] Loaded {len(df):,} records successfully.")
    return df


def extract_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Step 2 & 3: Convert timestamp and engineer temporal features.
    
    In machine learning, raw timestamp strings like '2016-01-01 12:30:00'
    cannot be directly used by models. We need to break down the time
    into structured numerical features:
    - year: Long-term trends (e.g., population growth over years)
    - month: Seasonal patterns (winter flu season, summer accidents)
    - day: Day of the month (1 to 31)
    - hour: Daily cycle (rush hours, night vs. daytime demand)
    - day_of_week: Weekly cycle (Monday = 0, Sunday = 6)
    - is_weekend: Binary flag (1 for Saturday/Sunday, 0 for weekdays)
    - date: Calendar date (YYYY-MM-DD) useful for daily demand aggregation
    """
    print("\n--- Converting 'timeStamp' to DateTime ---")
    # Convert 'timeStamp' column to pandas datetime object
    df["timeStamp"] = pd.to_datetime(df["timeStamp"], errors="coerce")
    
    # Check for invalid/unparseable timestamps
    invalid_timestamps = df["timeStamp"].isna().sum()
    print(f"[INFO] Invalid timestamps found: {invalid_timestamps}")
    if invalid_timestamps > 0:
        print(f"[WARNING] Dropping {invalid_timestamps} records with invalid timestamps.")
        df = df.dropna(subset=["timeStamp"]).copy()
    
    print("\n--- Extracting Temporal Features ---")
    # Extract year, month, day, hour
    df["year"] = df["timeStamp"].dt.year
    df["month"] = df["timeStamp"].dt.month
    df["day"] = df["timeStamp"].dt.day
    df["hour"] = df["timeStamp"].dt.hour
    
    # Extract day of week: Monday is 0, Sunday is 6
    df["day_of_week"] = df["timeStamp"].dt.dayofweek
    
    # Extract weekend indicator: 1 if Saturday (5) or Sunday (6), else 0
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    
    # Extract calendar date (YYYY-MM-DD) as a string for easy daily grouping later
    df["date"] = df["timeStamp"].dt.date
    
    print("[INFO] Extracted 7 time features: year, month, day, hour, day_of_week, is_weekend, date.")
    return df


def validate_features(df: pd.DataFrame) -> None:
    """
    Step 10: Run validation checks to ensure all features are within logical ranges.
    """
    print("\n==========================================")
    print("      RUNNING FEATURE VALIDATION CHECKS   ")
    print("==========================================")
    
    # Check 1: Year range (dataset covers 2015 to 2020)
    assert df["year"].between(2015, 2020).all(), "Validation Failed: Invalid year detected!"
    print(f"[PASS] Check 1: Years are within logical range ({df['year'].min()} to {df['year'].max()}).")
    
    # Check 2: Month range (1 to 12)
    assert df["month"].between(1, 12).all(), "Validation Failed: Month out of bounds (1-12)!"
    print(f"[PASS] Check 2: Months are within range 1 to 12.")
    
    # Check 3: Day range (1 to 31)
    assert df["day"].between(1, 31).all(), "Validation Failed: Day out of bounds (1-31)!"
    print(f"[PASS] Check 3: Days are within range 1 to 31.")
    
    # Check 4: Hour range (0 to 23)
    assert df["hour"].between(0, 23).all(), "Validation Failed: Hour out of bounds (0-23)!"
    print(f"[PASS] Check 4: Hours are within range 0 to 23.")
    
    # Check 5: Day of week range (0 to 6)
    assert df["day_of_week"].between(0, 6).all(), "Validation Failed: Day of week out of bounds (0-6)!"
    print(f"[PASS] Check 5: Day of week values are within range 0 (Mon) to 6 (Sun).")
    
    # Check 6: is_weekend is strictly binary (0 or 1)
    assert set(df["is_weekend"].unique()).issubset({0, 1}), "Validation Failed: is_weekend is not binary!"
    # Verify correspondence: Saturday(5) and Sunday(6) must match is_weekend == 1
    assert (df[df["day_of_week"].isin([5, 6])]["is_weekend"] == 1).all(), "Validation Failed: Weekend mapping mismatch!"
    assert (df[~df["day_of_week"].isin([5, 6])]["is_weekend"] == 0).all(), "Validation Failed: Weekday mapping mismatch!"
    print(f"[PASS] Check 6: 'is_weekend' flag correctly matches Saturday and Sunday.")
    
    # Check 7: No nulls in newly engineered columns
    new_cols = ["year", "month", "day", "hour", "day_of_week", "is_weekend", "date"]
    null_counts = df[new_cols].isna().sum().sum()
    assert null_counts == 0, f"Validation Failed: Found {null_counts} null values in new features!"
    print(f"[PASS] Check 7: Zero null values across all newly engineered features.")
    
    print("\n[SUCCESS] All feature validation checks PASSED successfully!")


def display_distributions(df: pd.DataFrame) -> None:
    """
    Step 6 & 7: Print dataset statistics and call distributions.
    """
    print("\n==========================================")
    print("            DATASET OVERVIEW              ")
    print("==========================================")
    print(f"Shape: {df.shape[0]:,} rows, {df.shape[1]} columns")
    print(f"Columns: {df.columns.tolist()}\n")
    
    print("--- First 5 Rows ---")
    print(df.head())
    
    print("\n==========================================")
    print("       CALL DISTRIBUTION BY HOUR (0-23)   ")
    print("==========================================")
    hourly_dist = df["hour"].value_counts().sort_index()
    print(f"{'Hour':<6} | {'Number of Calls':<16} | {'Percentage':<10}")
    print("-" * 38)
    total_calls = len(df)
    for hour, count in hourly_dist.items():
        pct = (count / total_calls) * 100
        print(f"{hour:<6} | {count:<16,} | {pct:.2f}%")
        
    print("\n==========================================")
    print("   CALL DISTRIBUTION BY DAY OF THE WEEK   ")
    print("==========================================")
    days_map = {
        0: "Monday",
        1: "Tuesday",
        2: "Wednesday",
        3: "Thursday",
        4: "Friday",
        5: "Saturday",
        6: "Sunday",
    }
    dow_dist = df["day_of_week"].value_counts().sort_index()
    print(f"{'Day':<12} (Index) | {'Number of Calls':<16} | {'Percentage':<10}")
    print("-" * 46)
    for dow, count in dow_dist.items():
        pct = (count / total_calls) * 100
        day_name = days_map.get(dow, "Unknown")
        print(f"{day_name:<12} ({dow})     | {count:<16,} | {pct:.2f}%")


def save_featured_dataset(df: pd.DataFrame, output_filepath: str) -> None:
    """
    Step 8: Save the resulting dataset to 'data/ems_features.csv'.
    """
    print(f"\n--- Saving Feature-Engineered Dataset ---")
    os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
    df.to_csv(output_filepath, index=False)
    print(f"[INFO] Successfully saved to '{output_filepath}'.")


def main():
    input_file = "data/ems_cleaned.csv"
    output_file = "data/ems_features.csv"
    
    # 1. Load cleaned data
    df = load_cleaned_data(input_file)
    
    # 2 & 3. Extract time features
    df = extract_time_features(df)
    
    # 4. Validate features
    validate_features(df)
    
    # 5. Display distributions and inspect head
    display_distributions(df)
    
    # 6. Save results
    save_featured_dataset(df, output_file)


if __name__ == "__main__":
    main()
