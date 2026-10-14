"""
AI-Based Emergency Ambulance Demand & Dispatch System
Step 5: Create a Complete Hourly Demand Dataset

This script expands the aggregated demand data from 'data/hourly_zone_demand.csv'
to include all zero-demand periods. 

Why this step is critical:
- In real life, an ambulance zone often experiences hours with 0 emergency calls.
- In 'data/hourly_zone_demand.csv', only hours with >= 1 call were recorded.
- Machine learning models cannot learn the true probability of emergencies if
  zero-call hours are omitted (it would create severe positive survivorship bias).
- We construct a full Cartesian product of (Dates × 24 Hours × 69 Zones), merge
  the observed call counts, and fill unobserved hours with demand = 0.

Output is saved to: 'data/complete_hourly_demand.csv'.
"""

import os
import pandas as pd


def load_aggregated_data(filepath: str) -> pd.DataFrame:
    """
    Step 1: Read the existing hourly zone demand dataset.
    """
    print(f"[INFO] Loading aggregated demand dataset from '{filepath}'...")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Input file not found at: {filepath}")
    
    df = pd.read_csv(filepath)
    print(f"[INFO] Loaded {len(df):,} non-zero demand records.")
    return df


def generate_complete_grid(df: pd.DataFrame) -> pd.DataFrame:
    """
    Steps 2, 3, 4 & 7: Generate a complete spatio-temporal grid.
    
    Every combination of:
    - Date: Every calendar day from min_date to max_date
    - Hour: 0 to 23 (24 hours per day)
    - Zone: All unique zones (townships) found in the dataset, including 'Unknown'
    """
    print("\n--- Generating Complete Spatio-Temporal Grid ---")
    min_date = df["date"].min()
    max_date = df["date"].max()
    print(f"[INFO] Date range identified: {min_date} to {max_date}")
    
    # 1. Full date range
    date_range = pd.date_range(start=min_date, end=max_date, freq="D")
    num_days = len(date_range)
    print(f"[INFO] Total calendar days: {num_days:,}")
    
    # 2. All 24 hours of the day
    hours = list(range(24))
    
    # 3. All unique zones (preserving 'Unknown')
    zones = sorted(df["twp"].unique())
    num_zones = len(zones)
    print(f"[INFO] Total unique zones: {num_zones} (including 'Unknown' if present)")
    
    expected_total_rows = num_days * len(hours) * num_zones
    print(f"[INFO] Generating complete grid: {num_days:,} days × 24 hours × {num_zones} zones = {expected_total_rows:,} rows...")
    
    # Use pandas MultiIndex.from_product for high speed and memory efficiency
    grid_index = pd.MultiIndex.from_product(
        [date_range, hours, zones],
        names=["dt_date", "hour", "twp"]
    )
    
    grid_df = pd.DataFrame(index=grid_index).reset_index()
    
    # Extract clean, deterministic date and time properties
    grid_df["date"] = grid_df["dt_date"].dt.strftime("%Y-%m-%d")
    grid_df["year"] = grid_df["dt_date"].dt.year.astype("int16")
    grid_df["month"] = grid_df["dt_date"].dt.month.astype("int8")
    grid_df["day_of_week"] = grid_df["dt_date"].dt.dayofweek.astype("int8")
    grid_df["is_weekend"] = grid_df["day_of_week"].isin([5, 6]).astype("int8")
    grid_df["hour"] = grid_df["hour"].astype("int8")
    
    # Drop temporary datetime object column to save memory
    grid_df = grid_df.drop(columns=["dt_date"])
    
    return grid_df


def merge_and_fill_demand(grid_df: pd.DataFrame, orig_df: pd.DataFrame) -> pd.DataFrame:
    """
    Steps 5 & 6: Merge original call counts and fill unobserved hours with demand = 0.
    """
    print("\n--- Merging Observed Demand onto Grid ---")
    
    # Keep only the essential merge keys and the demand count from original data
    merge_keys = ["date", "hour", "twp"]
    source_subset = orig_df[merge_keys + ["demand"]].copy()
    
    # Left merge: all grid rows are kept; hours with no calls will have NaN demand
    merged_df = grid_df.merge(source_subset, on=merge_keys, how="left")
    
    # Fill missing demand with integer 0
    print("[INFO] Filling unobserved hours with integer 0...")
    merged_df["demand"] = merged_df["demand"].fillna(0).astype("int32")
    
    # Order columns consistently
    column_order = [
        "date",
        "hour",
        "twp",
        "demand",
        "year",
        "month",
        "day_of_week",
        "is_weekend",
    ]
    merged_df = merged_df[column_order]
    
    return merged_df


def validate_complete_dataset(orig_df: pd.DataFrame, complete_df: pd.DataFrame) -> None:
    """
    Step 10: Run mandatory integrity checks on the completed dataset.
    """
    print("\n==========================================")
    print("      RUNNING INTEGRITY VERIFICATIONS     ")
    print("==========================================")
    
    # Check 1: Demand conservation (total calls must match exactly)
    total_demand_before = orig_df["demand"].sum()
    total_demand_after = complete_df["demand"].sum()
    assert total_demand_before == total_demand_after, (
        f"Validation Failed: Total demand mismatch! Before={total_demand_before}, After={total_demand_after}"
    )
    print(f"[PASS] Check 1: Total demand matches exactly ({total_demand_after:,} total calls).")
    
    # Check 2: No duplicates on (date, hour, twp)
    duplicates_count = complete_df.duplicated(subset=["date", "hour", "twp"]).sum()
    assert duplicates_count == 0, f"Validation Failed: Found {duplicates_count} duplicate (date, hour, twp) rows!"
    print("[PASS] Check 2: Zero duplicate combinations of (date, hour, twp).")
    
    # Check 3: Every zone has exactly 24 records per date
    records_per_zone_date = complete_df.groupby(["twp", "date"]).size()
    assert (records_per_zone_date == 24).all(), "Validation Failed: Not all zone-date pairs have exactly 24 hours!"
    print("[PASS] Check 3: Every zone has exactly 24 hourly records per date.")
    
    # Check 4: Demand values are strictly non-negative integers (>= 0)
    assert (complete_df["demand"] >= 0).all(), "Validation Failed: Found negative demand values!"
    assert pd.api.types.is_integer_dtype(complete_df["demand"]), "Validation Failed: Demand is not integer type!"
    print(f"[PASS] Check 4: Demand is strictly non-negative integers (Min: {complete_df['demand'].min()}, Max: {complete_df['demand'].max()}).")
    
    # Check 5: Zero missing values across all columns
    nulls_count = complete_df.isna().sum().sum()
    assert nulls_count == 0, f"Validation Failed: Found {nulls_count} missing values!"
    print("[PASS] Check 5: Zero missing values across the entire dataset.")
    
    print("\n[SUCCESS] All completeness validations PASSED successfully!")


def print_summary_metrics(orig_df: pd.DataFrame, complete_df: pd.DataFrame) -> None:
    """
    Step 9: Print all requested summary metrics and statistics.
    """
    print("\n==================================================================")
    print("             COMPLETE HOURLY DEMAND SUMMARY TABLE                ")
    print("==================================================================")
    print(f"{'Metric':<42} | {'Value':<20}")
    print("-" * 65)
    print(f"{'1. Original non-zero rows':<42} | {len(orig_df):,}")
    print(f"{'2. Completed total rows':<42} | {len(complete_df):,}")
    print(f"{'3. Number of unique zones':<42} | {complete_df['twp'].nunique()}")
    print(f"{'4. Minimum date':<42} | {complete_df['date'].min()}")
    print(f"{'5. Maximum date':<42} | {complete_df['date'].max()}")
    
    zero_demand_count = (complete_df["demand"] == 0).sum()
    zero_demand_pct = (zero_demand_count / len(complete_df)) * 100
    non_zero_demand_count = (complete_df["demand"] > 0).sum()
    
    print(f"{'6. Zero-demand rows count':<42} | {zero_demand_count:,}")
    print(f"{'7. Zero-demand percentage':<42} | {zero_demand_pct:.2f}%")
    print(f"{'8. Non-zero demand rows count':<42} | {non_zero_demand_count:,}")
    print(f"{'9. Total calls before completion':<42} | {orig_df['demand'].sum():,}")
    print(f"{'10. Total calls after completion':<42} | {complete_df['demand'].sum():,}")
    print("-" * 65)
    
    print("\n--- Sample of 10 Rows (Showing Both 0 and >0 Demand) ---")
    sample_rows = pd.concat([
        complete_df[complete_df["demand"] == 0].head(5),
        complete_df[complete_df["demand"] > 0].head(5)
    ]).sort_values(by=["date", "hour", "twp"])
    print(sample_rows.to_string(index=False))


def save_complete_dataset(df: pd.DataFrame, output_filepath: str) -> None:
    """
    Step 8: Save the complete dataset to CSV without modifying original files.
    """
    print(f"\n--- Saving Completed Dataset ---")
    os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
    df.to_csv(output_filepath, index=False)
    print(f"[INFO] Successfully saved {len(df):,} rows to '{output_filepath}'.")


def main():
    input_file = "data/hourly_zone_demand.csv"
    output_file = "data/complete_hourly_demand.csv"
    
    # 1. Load input dataset
    orig_df = load_aggregated_data(input_file)
    
    # 2. Generate full grid
    grid_df = generate_complete_grid(orig_df)
    
    # 3. Merge demand and fill missing with 0
    complete_df = merge_and_fill_demand(grid_df, orig_df)
    
    # 4. Validate completeness and integrity
    validate_complete_dataset(orig_df, complete_df)
    
    # 5. Print summary metrics
    print_summary_metrics(orig_df, complete_df)
    
    # 6. Save complete dataset
    save_complete_dataset(complete_df, output_file)


if __name__ == "__main__":
    main()
