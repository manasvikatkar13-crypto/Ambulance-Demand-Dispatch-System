"""
AI-Based Emergency Ambulance Demand & Dispatch System
Step 6: Historical Weather Feature Integration

This script fetches hourly historical weather data from the Open-Meteo
Historical Weather API for Montgomery County, Pennsylvania, and merges
it into our complete hourly demand dataset.

Representative Coordinates:
- Latitude : 40.1700° N
- Longitude: -75.3200° W
- Location : Geographic center of Montgomery County, PA (Worcester/East Norriton)

NOTE ON GEOGRAPHIC SCOPE:
Weather data is retrieved for this single representative central coordinate,
representing county-level ambient weather conditions. It is applied across all
townships because macro-weather phenomena (temperature waves, snowstorms, heavy
rain) operate at a county-wide scale.

Output is saved to: 'data/demand_with_weather.csv'.
"""

import os
import sys
import time
import json
import urllib.request
import urllib.error
import pandas as pd

# Central geographical coordinates for Montgomery County, PA
MONTGOMERY_COUNTY_LAT = 40.17
MONTGOMERY_COUNTY_LNG = -75.32
LOCATION_DESCRIPTION = "Geographic Center of Montgomery County, PA (Worcester / East Norriton)"

# Open-Meteo Historical Weather API endpoint
API_URL = "https://archive-api.open-meteo.com/v1/archive"


def load_demand_data(filepath: str) -> pd.DataFrame:
    """
    Step 1: Read the complete hourly demand dataset without modifying it.
    """
    print(f"[INFO] Reading complete demand dataset from '{filepath}'...")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Input file not found at: {filepath}")
    
    df = pd.read_csv(filepath)
    print(f"[INFO] Loaded {len(df):,} rows across {df['twp'].nunique()} zones.")
    return df


def fetch_open_meteo_weather(
    lat: float,
    lon: float,
    start_date: str,
    end_date: str,
    max_retries: int = 3,
    timeout: int = 90
) -> tuple[pd.DataFrame, dict]:
    """
    Steps 2, 3, 4 & 5: Fetch hourly historical weather data from Open-Meteo.
    
    Requested Variables:
    - temperature_2m        : Air temperature at 2 metres above ground (°C)
    - relative_humidity_2m  : Relative humidity at 2 metres above ground (%)
    - precipitation         : Total precipitation (rain + snow water equivalent) (mm)
    - wind_speed_10m        : Wind speed at 10 metres above ground (km/h)
    - weather_code          : WMO Weather Interpretation Code
    """
    print("\n--- Step 6.1: Fetching Weather Data from Open-Meteo API ---")
    print(f"[INFO] Selected Central Coordinates : Lat {lat:.4f}° N, Lng {lon:.4f}° W")
    print(f"[INFO] Location Description          : {LOCATION_DESCRIPTION}")
    print(f"[INFO] Note on Spatial Coverage      : County-level weather (single representative station)")
    print(f"[INFO] Target Date Range             : {start_date} to {end_date}")
    
    params = [
        f"latitude={lat}",
        f"longitude={lon}",
        f"start_date={start_date}",
        f"end_date={end_date}",
        "hourly=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code",
        "timezone=America%2FNew_York"
    ]
    query_url = f"{API_URL}?{'&'.join(params)}"
    print(f"[INFO] Querying Open-Meteo Archive API...")
    
    response_data = None
    headers = {"User-Agent": "Ambulance-Demand-Dispatch-System/1.0 (College Mini-Project)"}
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"[INFO] API Request Attempt {attempt} of {max_retries}...")
            req = urllib.request.Request(query_url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status == 200:
                    raw_text = response.read().decode("utf-8")
                    response_data = json.loads(raw_text)
                    print("[INFO] API response received successfully (HTTP 200 OK)!")
                    break
                else:
                    print(f"[WARNING] Server returned status code: {response.status}")
        except urllib.error.URLError as e:
            print(f"[WARNING] Network/HTTP error during attempt {attempt}: {e}")
            if attempt < max_retries:
                wait_seconds = attempt * 5
                print(f"[INFO] Retrying in {wait_seconds} seconds...")
                time.sleep(wait_seconds)
        except Exception as e:
            print(f"[WARNING] Unexpected error: {e}")
            if attempt < max_retries:
                time.sleep(5)
                
    if response_data is None or "hourly" not in response_data:
        print("\n[ERROR] Failed to retrieve weather data from Open-Meteo API.")
        print("[ERROR] Please check your internet connection or verify Open-Meteo service availability.")
        print("[ERROR] To retry: Check internet connection and rerun `python src/add_weather_features.py`.")
        sys.exit(1)
        
    # Extract hourly records and units dictionary
    hourly_dict = response_data["hourly"]
    units_dict = response_data.get("hourly_units", {})
    
    # Build weather DataFrame
    weather_df = pd.DataFrame(hourly_dict)
    
    # Parse date and hour from the ISO 8601 string (e.g. '2015-12-10T00:00')
    weather_df["date"] = weather_df["time"].str[:10]
    weather_df["hour"] = weather_df["time"].str[11:13].astype("int8")
    
    # Drop original ISO time string
    weather_df = weather_df.drop(columns=["time"])
    
    print(f"[INFO] Parsed {len(weather_df):,} hourly weather observations.")
    return weather_df, units_dict


def merge_weather_features(demand_df: pd.DataFrame, weather_df: pd.DataFrame) -> pd.DataFrame:
    """
    Step 6: Merge weather features into demand dataset using (date, hour).
    """
    print("\n--- Step 6.2: Merging Weather Features with Hourly Demand ---")
    initial_rows = len(demand_df)
    initial_demand = demand_df["demand"].sum()
    
    # Left merge: all demand rows are preserved exactly
    merged_df = demand_df.merge(weather_df, on=["date", "hour"], how="left")
    
    print(f"[INFO] Merge completed. Total rows: {len(merged_df):,}")
    return merged_df, initial_rows, initial_demand


def validate_merged_data(
    merged_df: pd.DataFrame,
    initial_rows: int,
    initial_demand: int,
    weather_cols: list
) -> None:
    """
    Step 9: Run strict validation checks.
    """
    print("\n==========================================")
    print("      RUNNING INTEGRITY VERIFICATIONS     ")
    print("==========================================")
    
    # Check 1: Row count preservation
    assert len(merged_df) == initial_rows, (
        f"Validation Failed: Row count changed! Initial={initial_rows:,}, Merged={len(merged_df):,}"
    )
    print(f"[PASS] Check 1: Row count conserved exactly ({initial_rows:,} rows).")
    
    # Check 2: Total demand conservation
    merged_demand = merged_df["demand"].sum()
    assert merged_demand == initial_demand, (
        f"Validation Failed: Total demand altered! Initial={initial_demand:,}, Merged={merged_demand:,}"
    )
    print(f"[PASS] Check 2: Total demand conserved perfectly ({initial_demand:,} calls).")
    
    # Check 3: Check for missing values in weather features
    weather_nulls = merged_df[weather_cols].isna().sum()
    print("[INFO] Weather feature missing counts:")
    for col, null_count in weather_nulls.items():
        print(f"  - {col:<22}: {null_count} missing")
    assert weather_nulls.sum() == 0, "Validation Failed: Found missing values in weather features!"
    print("[PASS] Check 3: Zero missing values in newly merged weather columns.")
    
    # Check 4: Check logical value ranges for weather
    assert merged_df["temperature_2m"].between(-30, 45).all(), "Validation Failed: Extreme temperature outlier!"
    assert merged_df["relative_humidity_2m"].between(0, 100).all(), "Validation Failed: Humidity outside 0-100%!"
    assert (merged_df["precipitation"] >= 0).all(), "Validation Failed: Negative precipitation found!"
    assert (merged_df["wind_speed_10m"] >= 0).all(), "Validation Failed: Negative wind speed found!"
    print("[PASS] Check 4: All weather values lie within physically logical meteorological ranges.")
    
    print("\n[SUCCESS] All weather integration verifications PASSED successfully!")


def print_weather_summary(
    merged_df: pd.DataFrame,
    units_dict: dict,
    initial_demand: int,
    weather_cols: list
) -> None:
    """
    Step 8: Print comprehensive execution summary.
    """
    print("\n==================================================================")
    print("             WEATHER INTEGRATION SUMMARY REPORT                   ")
    print("==================================================================")
    print(f"{'Metric':<38} | {'Value':<26}")
    print("-" * 67)
    print(f"{'Representative Latitude':<38} | {MONTGOMERY_COUNTY_LAT}° N")
    print(f"{'Representative Longitude':<38} | {MONTGOMERY_COUNTY_LNG}° W")
    print(f"{'Location Description':<38} | {LOCATION_DESCRIPTION}")
    print(f"{'Spatial Weather Granularity':<38} | County-level (applied uniformly)")
    print(f"{'Start Date':<38} | {merged_df['date'].min()}")
    print(f"{'End Date':<38} | {merged_df['date'].max()}")
    print(f"{'Output Shape (Rows, Columns)':<38} | {merged_df.shape[0]:,} rows, {merged_df.shape[1]} columns")
    print(f"{'Total Demand Before Merging':<38} | {initial_demand:,} calls")
    print(f"{'Total Demand After Merging':<38} | {merged_df['demand'].sum():,}")
    print("-" * 67)
    
    print("\nWeather Variables and Measurement Units:")
    print("-" * 55)
    for col in weather_cols:
        unit = units_dict.get(col, "N/A")
        print(f"  - {col:<22} : Unit = '{unit}'")
        
    print("\nMissing Values Count per Column:")
    print("-" * 55)
    for col in merged_df.columns:
        null_count = merged_df[col].isna().sum()
        print(f"  - {col:<22} : {null_count} nulls")
        
    print("\nFirst 5 Rows of Feature-Enriched Dataset:")
    print("-" * 67)
    print(merged_df.head().to_string(index=False))
    print("==================================================================")


def save_merged_data(df: pd.DataFrame, output_filepath: str) -> None:
    """
    Step 7: Save the result to CSV without modifying existing files.
    """
    print(f"\n--- Saving Final Dataset ---")
    os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
    df.to_csv(output_filepath, index=False)
    print(f"[INFO] Successfully saved to '{output_filepath}'.")


def main():
    input_file = "data/complete_hourly_demand.csv"
    output_file = "data/demand_with_weather.csv"
    
    # 1. Load complete demand dataset
    demand_df = load_demand_data(input_file)
    start_date = demand_df["date"].min()
    end_date = demand_df["date"].max()
    
    # 2 & 3. Fetch historical weather from Open-Meteo
    weather_df, units_dict = fetch_open_meteo_weather(
        lat=MONTGOMERY_COUNTY_LAT,
        lon=MONTGOMERY_COUNTY_LNG,
        start_date=start_date,
        end_date=end_date
    )
    
    # 4. Merge weather features
    weather_cols = [
        "temperature_2m",
        "relative_humidity_2m",
        "precipitation",
        "wind_speed_10m",
        "weather_code"
    ]
    merged_df, initial_rows, initial_demand = merge_weather_features(demand_df, weather_df)
    
    # 5. Validation checks
    validate_merged_data(merged_df, initial_rows, initial_demand, weather_cols)
    
    # 6. Print summary
    print_weather_summary(merged_df, units_dict, initial_demand, weather_cols)
    
    # 7. Save output
    save_merged_data(merged_df, output_file)


if __name__ == "__main__":
    main()
