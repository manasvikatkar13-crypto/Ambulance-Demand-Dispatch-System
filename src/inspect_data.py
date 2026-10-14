import pandas as pd
import os

def inspect_dataset(filepath):
    print(f"--- Inspecting Dataset: {filepath} ---")
    if not os.path.exists(filepath):
        print(f"Error: File not found at {filepath}")
        return

    try:
        # Check file format and load
        file_ext = os.path.splitext(filepath)[1]
        print(f"File Format: {file_ext}")
        
        if file_ext == '.csv':
            df = pd.read_csv(filepath)
        else:
            print("Unsupported file format for this inspection script.")
            return

        print("\n--- Basic Information ---")
        print(f"Number of rows: {df.shape[0]}")
        print(f"Number of columns: {df.shape[1]}")
        print("\n--- Column Names ---")
        print(df.columns.tolist())
        
        print("\n--- Data Types ---")
        print(df.dtypes)
        
        print("\n--- Missing Values ---")
        print(df.isnull().sum())
        
        print("\n--- Duplicate Records ---")
        print(f"Number of duplicate rows: {df.duplicated().sum()}")
        
        print("\n--- First Five Rows ---")
        print(df.head())
        
    except Exception as e:
        print(f"Error reading or processing the file: {e}")

if __name__ == "__main__":
    filepath = "data/911.csv"
    inspect_dataset(filepath)
