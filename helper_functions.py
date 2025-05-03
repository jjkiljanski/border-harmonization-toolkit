import pandas as pd
import json
import os
from datetime import datetime

def load_and_clean_csv(file_path, district_registry):
    # Read the CSV
    df = pd.read_csv(file_path)

    if {'region', 'district'}.issubset(df.columns):
        df['region'] = df['region'].str.upper()
        df['district'] = df['district'].str.upper()

    r_d_aim_new = []
    d_not_in_registry = []

    for idx, dist_aim in df['district'].items():
        dist_name = district_registry.find_district(dist_aim)
        if dist_name is None:
            d_not_in_registry.append(dist_aim)
        elif dist_name != dist_aim:
            print(f"Warning: name {dist_aim} is an alternative district name. Processing further as {dist_name}")

        df.at[idx, 'district'] = dist_name

    if d_not_in_registry:
            raise ValueError(f"District names {d_not_in_registry} do not exist in the district registry.")

    return df

def load_config(config_path="config.json"):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file {config_path} not found.")
    
    with open(config_path, "r") as config_file:
        config_data = json.load(config_file)
    
    # Convert global_timespan start and end dates to datetime objects
    global_timespan = config_data.get("global_timespan", {})
    if "start" in global_timespan:
        global_timespan["start"] = datetime.strptime(global_timespan["start"], "%Y-%m-%d")
    if "end" in global_timespan:
        global_timespan["end"] = datetime.strptime(global_timespan["end"], "%Y-%m-%d")
    
    return config_data