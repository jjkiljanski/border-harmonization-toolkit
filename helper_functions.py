import pandas as pd

def load_and_clean_csv(file_path, district_registry):
    # Read the CSV
    df = pd.read_csv(file_path)

    if {'region', 'district'}.issubset(df.columns):
        df['region'] = df['region'].str.upper()
        df['district'] = df['district'].str.upper()

    r_d_aim_new = []
    d_not_in_registry = []

    for idx, dist_aim in df['district'].items():
        region = df.at[idx, 'region']  # get corresponding region
        dist_name = district_registry.find_district(dist_aim)

        if dist_name is None:
            d_not_in_registry.append(dist_aim)
        elif dist_name != dist_aim:
            print(f"Warning: name {dist_aim} is an alternative district name. Processing further as {dist_name}")

        df.at[idx, 'region'] = dist_name

    if d_not_in_registry:
            raise ValueError(f"District names {d_not_in_registry} do not exist in the district registry.")

    return df

    # Create list of (REGION, DISTRICT) pairs in uppercase
    #r_d_pairs = list(zip(df['region'], df['district']))