"""
AI-Based Emergency Ambulance Demand & Dispatch System
Step 4: Hourly Ambulance Demand Aggregation by Zone

This script aggregates individual emergency medical calls from 'data/ems_features.csv'
into hourly demand counts for each geographical zone (township/municipality).
Each row in the resulting dataset represents the total ambulance demand for a specific
zone during a specific one-hour window.

Output is saved to: 'data/hourly_zone_demand.csv'.
"""

import os
import pandas as pd


def load_feature_data(filepath: str) -> pd.DataFrame:
    """
    Step 1: Load the feature-engineered dataset without modifying it.
    """
    print(f"[INFO] Loading input dataset from '{filepath}'...")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Input file not found at: {filepath}")
    
    df = pd.read_csv(filepath)
    print(f"[INFO] Successfully loaded {len(df):,} individual EMS call records.")
    return df


def aggregate_hourly_demand(df: pd.DataFrame) -> pd.DataFrame:
    """
    Steps 2, 3, 4 & 5: Group by (date, hour, twp) and aggregate demand.
    
    Why aggregation is needed:
    - Raw emergency data logs individual calls as they happen (point events).
    - For AI forecasting and dispatch planning, ambulance dispatchers need to predict:
      "How many ambulances will be needed in Township X between 10:00 AM and 11:00 AM tomorrow?"
    - Therefore, we group records by (date, hour, twp) and count the calls.
    - We also preserve the deterministic temporal features (year, month, day_of_week, is_weekend).
    """
    print("\n--- Aggregating Calls by Date, Hour, and Zone ---")
    
    # Ensure missing or NaN townships are grouped as 'Unknown'
    df["twp"] = df["twp"].fillna("Unknown")
    
    # Group by date, hour, zone, and the associated calendar features
    grouping_cols = ["date", "hour", "twp", "year", "month", "day_of_week", "is_weekend"]
    
    # Calculate demand: count of calls in each group
    agg_df = (
        df.groupby(grouping_cols, as_index=False)
        .size()
        .rename(columns={"size": "demand"})
    )
    
    # Reorder columns logically for clean readability
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
    agg_df = agg_df[column_order]
    
    print(f"[INFO] Aggregation complete. Result contains {len(agg_df):,} zone-hour rows.")
    return agg_df


def run_validation_checks(raw_df: pd.DataFrame, agg_df: pd.DataFrame) -> None:
    """
    Steps 8 & 9: Run essential data validation checks.
    """
    print("\n==========================================")
    print("      RUNNING AGGREGATION VALIDATION      ")
    print("==========================================")
    
    # Check 1: Call total conservation (no calls lost or created)
    total_raw_calls = len(raw_df)
    total_agg_demand = agg_df["demand"].sum()
    assert total_raw_calls == total_agg_demand, (
        f"Validation Failed: Call counts mismatch! Raw={total_raw_calls}, Aggregated={total_agg_demand}"
    )
    print(f"[PASS] Check 1: Total call count conserved perfectly ({total_raw_calls:,} calls).")
    
    # Check 2: No duplicate (date, hour, twp) combinations
    dup_combos = agg_df.duplicated(subset=["date", "hour", "twp"]).sum()
    assert dup_combos == 0, f"Validation Failed: Found {dup_combos} duplicate (date, hour, twp) rows!"
    print("[PASS] Check 2: Zero duplicate combinations of (date, hour, twp).")
    
    # Check 3: Demand contains strictly positive integers (>= 1)
    assert (agg_df["demand"] > 0).all(), "Validation Failed: Found demand values <= 0!"
    assert pd.api.types.is_integer_dtype(agg_df["demand"]), "Validation Failed: Demand is not integer!"
    print(f"[PASS] Check 3: Demand values are strictly positive integers (Min: {agg_df['demand'].min()}, Max: {agg_df['demand'].max()}).")
    
    # Check 4: Zero null values in any aggregated column
    nulls_count = agg_df.isna().sum().sum()
    assert nulls_count == 0, f"Validation Failed: Found {nulls_count} missing values in aggregated dataset!"
    print("[PASS] Check 4: Zero missing values across all columns.")
    
    print("\n[SUCCESS] All aggregation validation checks PASSED successfully!")


def print_demand_statistics(raw_df: pd.DataFrame, agg_df: pd.DataFrame) -> None:
    """
    Step 7: Print detailed metrics, top zones, peak demand hours, and sample rows.
    """
    print("\n==========================================")
    print("        AGGREGATED DATASET OVERVIEW       ")
    print("==========================================")
    print(f"Shape: {agg_df.shape[0]:,} rows, {agg_df.shape[1]} columns")
    print(f"Columns: {agg_df.columns.tolist()}")
    
    n_unique_zones = agg_df["twp"].nunique()
    print(f"Number of unique zones (twp): {n_unique_zones}")
    
    print("\nCall Count Conservation Check:")
    print(f"  - Total calls in ems_features.csv  : {len(raw_df):,}")
    print(f"  - Sum of demand in aggregated file : {agg_df['demand'].sum():,}")
    print(f"  - Difference                       : {len(raw_df) - agg_df['demand'].sum():,} (Exact match)")
    
    print("\n--- First 10 Rows ---")
    print(agg_df.head(10).to_string(index=False))
    
    print("\n==========================================")
    print("      TOP 5 ZONES BY TOTAL DEMAND         ")
    print("==========================================")
    top_zones = (
        agg_df.groupby("twp")["demand"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
    )
    print(f"{'Rank':<5} | {'Zone (Township)':<22} | {'Total Calls':<12} | {'Percentage':<10}")
    print("-" * 57)
    for rank, (zone, total) in enumerate(top_zones.items(), start=1):
        pct = (total / len(raw_df)) * 100
        print(f"{rank:<5} | {zone:<22} | {total:<12,} | {pct:.2f}%")
        
    print("\n==========================================")
    print("   TOP 5 DATE-HOUR-ZONE PEAK DEMAND       ")
    print("==========================================")
    top_peaks = agg_df.sort_values(by="demand", ascending=False).head(5)
    print(f"{'Date':<12} | {'Hour':<5} | {'Zone (Township)':<20} | {'Demand (Calls)':<15}")
    print("-" * 60)
    for _, row in top_peaks.iterrows():
        print(f"{row['date']:<12} | {row['hour']:<5} | {row['twp']:<20} | {row['demand']:<15}")


def save_aggregated_data(df: pd.DataFrame, output_filepath: str) -> None:
    """
    Step 6: Save the resulting aggregated dataset to disk.
    """
    print(f"\n--- Saving Aggregated Dataset ---")
    os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
    df.to_csv(output_filepath, index=False)
    print(f"[INFO] Successfully saved to '{output_filepath}'.")


def main():
    input_filepath = "data/ems_features.csv"
    output_filepath = "data/hourly_zone_demand.csv"
    
    # 1. Load input dataset
    raw_df = load_feature_data(input_filepath)
    
    # 2. Aggregate demand
    agg_df = aggregate_hourly_demand(raw_df)
    
    # 3. Validate aggregation
    run_validation_checks(raw_df, agg_df)
    
    # 4. Print summaries and distributions
    print_demand_statistics(raw_df, agg_df)
    
    # 5. Save output
    save_aggregated_data(agg_df, output_filepath)


if __name__ == "__main__":
    main()
