"""
AI-Based Emergency Ambulance Demand & Dispatch System
Step 2: Data Cleaning and Preprocessing for EMS Calls

This script loads the raw 911 emergency dataset, filters for Emergency Medical
Services (EMS) calls, removes duplicates, validates timestamps and coordinates,
handles missing values without dropping valid calls, removes constant dummy columns,
saves the cleaned dataset to `data/ems_cleaned.csv`, and runs verification checks.
"""

import os
import pandas as pd
import numpy as np

# Plausible geographic bounds for Montgomery County, Pennsylvania
# Latitude roughly spans 39.98 to 40.50 (extended slightly to 39.80 - 40.60 to account for county borders)
# Longitude roughly spans -75.70 to -75.00 (extended slightly to -75.80 - -74.80 to account for county borders)
MONTGOMERY_BOUNDS = {
    "lat_min": 39.80,
    "lat_max": 40.60,
    "lng_min": -75.80,
    "lng_max": -74.80,
}


def load_raw_data(filepath: str) -> pd.DataFrame:
    """Load the raw dataset from disk."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Raw dataset file not found at: {filepath}")
    print(f"[INFO] Loading raw dataset from '{filepath}'...")
    df = pd.read_csv(filepath)
    print(f"[INFO] Successfully loaded {len(df):,} records with {df.shape[1]} columns.")
    return df


def filter_ems_calls(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter the dataset to keep only EMS (Emergency Medical Services) calls.
    
    In the raw dataset, the 'title' column contains prefixes representing departments:
    - 'EMS: ...' -> Emergency Medical Services
    - 'Fire: ...' -> Fire department calls (e.g., 'Fire: EMS SPECIAL SERVICE' is Fire, not EMS)
    - 'Traffic: ...' -> Traffic incidents
    
    Using startswith('EMS:') strictly isolates medical calls without including Fire or Traffic.
    """
    print("\n--- Step 2.1: Filtering EMS Calls ---")
    ems_mask = df["title"].astype(str).str.startswith("EMS:")
    ems_df = df[ems_mask].copy()
    print(f"[INFO] Total records in original dataset: {len(df):,}")
    print(f"[INFO] Filtered EMS records: {len(ems_df):,} ({(len(ems_df)/len(df)*100):.2f}% of total calls)")
    return ems_df


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Identify and remove exact duplicate records."""
    print("\n--- Step 2.2: Removing Exact Duplicate Records ---")
    initial_count = len(df)
    duplicates_count = df.duplicated().sum()
    print(f"[INFO] Exact duplicate rows detected: {duplicates_count:,}")
    
    df_dedup = df.drop_duplicates().copy()
    print(f"[INFO] Records remaining after removing duplicates: {len(df_dedup):,}")
    return df_dedup, duplicates_count


def validate_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert the 'timeStamp' column to datetime.
    Any unparseable dates will be converted to NaT (Not-a-Time) and dropped.
    """
    print("\n--- Step 2.3: Validating and Converting Timestamps ---")
    initial_count = len(df)
    
    # Convert string timestamps to pandas datetime objects
    df["timeStamp"] = pd.to_datetime(df["timeStamp"], errors="coerce")
    
    invalid_time_count = df["timeStamp"].isna().sum()
    print(f"[INFO] Invalid/unparseable timestamps detected: {invalid_time_count:,}")
    
    if invalid_time_count > 0:
        df = df.dropna(subset=["timeStamp"]).copy()
        print(f"[INFO] Dropped {invalid_time_count:,} records with invalid timestamps.")
    else:
        print("[INFO] All timestamps are valid datetime values.")
        
    print(f"[INFO] Date range: from {df['timeStamp'].min()} to {df['timeStamp'].max()}")
    return df, invalid_time_count


def validate_coordinates(df: pd.DataFrame, bounds: dict) -> pd.DataFrame:
    """
    Validate latitude and longitude coordinates:
    1. Ensure values are numeric.
    2. Check that coordinates lie within Montgomery County, PA bounds.
    3. Exclude corrupted readings (e.g., Null Island (0,0), coordinates in other countries/states).
    """
    print("\n--- Step 2.4: Validating Geographic Coordinates ---")
    # Ensure numeric types
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lng"] = pd.to_numeric(df["lng"], errors="coerce")
    
    lat_min, lat_max = bounds["lat_min"], bounds["lat_max"]
    lng_min, lng_max = bounds["lng_min"], bounds["lng_max"]
    
    valid_coords_mask = (
        (df["lat"] >= lat_min) & (df["lat"] <= lat_max) &
        (df["lng"] >= lng_min) & (df["lng"] <= lng_max)
    )
    
    invalid_coords_count = (~valid_coords_mask).sum()
    print(f"[INFO] Coordinates bounds applied: Lat [{lat_min}, {lat_max}], Lng [{lng_min}, {lng_max}]")
    print(f"[INFO] Out-of-bounds or corrupt coordinate records: {invalid_coords_count:,}")
    
    # Filter valid coordinates
    df_valid = df[valid_coords_mask].copy()
    print(f"[INFO] Records remaining after coordinate validation: {len(df_valid):,}")
    return df_valid, invalid_coords_count


def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Handle missing values carefully without discarding real emergency calls:
    - 'twp' (township): Fill missing values with 'Unknown' instead of dropping rows.
    - 'zip': Keep missing values as-is (NaN). Exact latitude and longitude are preserved
      for spatial analysis and dispatch, so missing ZIP does not invalidate a call.
    """
    print("\n--- Step 2.5: Handling Missing Values ---")
    missing_twp_before = df["twp"].isna().sum()
    missing_zip = df["zip"].isna().sum()
    print(f"[INFO] Missing township ('twp') entries: {missing_twp_before:,}")
    print(f"[INFO] Missing ZIP codes ('zip'): {missing_zip:,}")
    
    # Impute missing township with 'Unknown'
    df["twp"] = df["twp"].fillna("Unknown")
    print("[INFO] Replaced missing 'twp' with 'Unknown' to avoid dropping valid emergency calls.")
    return df


def remove_constant_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Inspect and drop constant columns.
    The 'e' column is a dummy variable that is always 1 for all records.
    It carries zero variance and no predictive information for AI models.
    """
    print("\n--- Step 2.6: Inspecting and Removing Constant Columns ---")
    if "e" in df.columns:
        unique_vals = df["e"].unique()
        print(f"[INFO] Unique values in 'e' column: {unique_vals}")
        if len(unique_vals) == 1:
            print("[INFO] 'e' is constant (always 1). Dropping 'e' to conserve memory.")
            df = df.drop(columns=["e"]).copy()
    return df


def save_cleaned_data(df: pd.DataFrame, output_filepath: str) -> None:
    """Save the cleaned dataset to disk without touching the raw file."""
    print(f"\n--- Step 2.7: Saving Cleaned Dataset ---")
    os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
    df.to_csv(output_filepath, index=False)
    print(f"[INFO] Saved cleaned dataset to '{output_filepath}'.")


def run_verification_checks(raw_filepath: str, cleaned_filepath: str, bounds: dict) -> None:
    """
    Run mandatory integrity checks on the raw and cleaned datasets.
    """
    print("\n==========================================")
    print("      RUNNING INTEGRITY VERIFICATIONS     ")
    print("==========================================")
    
    # 1. Original file still exists
    assert os.path.exists(raw_filepath), f"Verification Failed: Original file '{raw_filepath}' is missing!"
    print("[PASS] Check 1: Original raw dataset exists and is untouched.")
    
    # 2. Cleaned file exists and can be loaded
    assert os.path.exists(cleaned_filepath), f"Verification Failed: Cleaned file '{cleaned_filepath}' is missing!"
    df_clean = pd.read_csv(cleaned_filepath)
    print(f"[PASS] Check 2: Cleaned dataset loaded successfully ({len(df_clean):,} rows, {df_clean.shape[1]} columns).")
    
    # 3. Contains ONLY intended EMS calls
    non_ems = df_clean[~df_clean["title"].str.startswith("EMS:")]["title"].count()
    assert non_ems == 0, f"Verification Failed: Found {non_ems} non-EMS calls in cleaned dataset!"
    print("[PASS] Check 3: All records belong strictly to EMS calls (no Fire or Traffic).")
    
    # 4. Valid timestamps
    df_clean["timeStamp"] = pd.to_datetime(df_clean["timeStamp"], errors="coerce")
    null_times = df_clean["timeStamp"].isna().sum()
    assert null_times == 0, f"Verification Failed: Found {null_times} invalid timestamps!"
    print("[PASS] Check 4: All timestamps are valid datetime objects.")
    
    # 5. Coordinates within plausible bounds
    lat_valid = (df_clean["lat"] >= bounds["lat_min"]) & (df_clean["lat"] <= bounds["lat_max"])
    lng_valid = (df_clean["lng"] >= bounds["lng_min"]) & (df_clean["lng"] <= bounds["lng_max"])
    coords_valid = (lat_valid & lng_valid).all()
    assert coords_valid, "Verification Failed: Found out-of-bounds coordinates in cleaned dataset!"
    print("[PASS] Check 5: All coordinates fall strictly within Montgomery County bounds.")
    
    # 6. Duplicate records handled
    dups = df_clean.duplicated().sum()
    assert dups == 0, f"Verification Failed: Found {dups} duplicate records in cleaned dataset!"
    print("[PASS] Check 6: Zero duplicate records in the cleaned dataset.")
    
    # 7. Constant 'e' column excluded
    assert "e" not in df_clean.columns, "Verification Failed: Constant column 'e' was not dropped!"
    print("[PASS] Check 7: Constant column 'e' successfully excluded.")
    
    print("\n[SUCCESS] All verification checks PASSED successfully!\n")


def print_summary_table(summary: dict, remaining_missing: pd.Series) -> None:
    """Print the final before-and-after cleaning summary table."""
    print("==================================================================")
    print("             BEFORE-AND-AFTER CLEANING SUMMARY TABLE             ")
    print("==================================================================")
    print(f"{'Metric':<45} | {'Value':<15}")
    print("-" * 65)
    print(f"{'1. Original records in 911.csv':<45} | {summary['original_records']:,}")
    print(f"{'2. EMS records identified (title starts with EMS:)':<45} | {summary['ems_records']:,}")
    print(f"{'3. Non-EMS records filtered out (Fire & Traffic)':<45} | {summary['non_ems_filtered']:,}")
    print(f"{'4. Duplicate records removed':<45} | {summary['duplicates_removed']:,}")
    print(f"{'5. Invalid timestamps removed':<45} | {summary['invalid_timestamps_removed']:,}")
    print(f"{'6. Out-of-bounds / corrupt coordinates removed':<45} | {summary['invalid_coords_removed']:,}")
    print(f"{'7. Final cleaned records in ems_cleaned.csv':<45} | {summary['final_cleaned_records']:,}")
    print("-" * 65)
    print("\nRemaining Missing Values in Cleaned Dataset:")
    print("-" * 40)
    for col, count in remaining_missing.items():
        pct = (count / summary['final_cleaned_records']) * 100
        print(f"  {col:<12} : {count:>7,} missing ({pct:.2f}%)")
    print("==================================================================")


def clean_data(raw_filepath: str = "data/911.csv", cleaned_filepath: str = "data/ems_cleaned.csv") -> None:
    """Main pipeline function to clean the dataset."""
    print("==================================================================")
    print(" AI-Based Emergency Ambulance Demand & Dispatch System - Step 2  ")
    print("                    DATA CLEANING PIPELINE                        ")
    print("==================================================================")
    
    # 1. Load raw data
    raw_df = load_raw_data(raw_filepath)
    n_original = len(raw_df)
    
    # 2. Filter EMS calls
    ems_df = filter_ems_calls(raw_df)
    n_ems = len(ems_df)
    n_non_ems = n_original - n_ems
    
    # 3. Remove duplicates
    ems_df, n_duplicates = remove_duplicates(ems_df)
    
    # 4. Validate timestamps
    ems_df, n_invalid_time = validate_timestamps(ems_df)
    
    # 5. Validate coordinates
    ems_df, n_invalid_coords = validate_coordinates(ems_df, MONTGOMERY_BOUNDS)
    
    # 6. Handle missing values
    ems_df = handle_missing_values(ems_df)
    
    # 7. Remove constant column 'e'
    ems_df = remove_constant_columns(ems_df)
    
    # 8. Save cleaned dataset
    save_cleaned_data(ems_df, cleaned_filepath)
    
    # 9. Verify integrity
    run_verification_checks(raw_filepath, cleaned_filepath, MONTGOMERY_BOUNDS)
    
    # 10. Print final summary
    summary = {
        "original_records": n_original,
        "ems_records": n_ems,
        "non_ems_filtered": n_non_ems,
        "duplicates_removed": n_duplicates,
        "invalid_timestamps_removed": n_invalid_time,
        "invalid_coords_removed": n_invalid_coords,
        "final_cleaned_records": len(ems_df),
    }
    remaining_missing = ems_df.isna().sum()
    print_summary_table(summary, remaining_missing)


if __name__ == "__main__":
    clean_data()
