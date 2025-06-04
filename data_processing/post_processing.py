import pandas as pd
import os

from core.core import AdministrativeHistory
from data_models.harmonization_config import SumUpDatasetsArgs

def sum_up_datasets(administrative_history: AdministrativeHistory, arguments: SumUpDatasetsArgs) -> None:
    folder = administrative_history.data_harmonization_output_folder
    print(f"🟡 Starting sum_up_datasets: {arguments.datasets_list} -> {arguments.new_dataset_name}.csv")

    dfs = []

    # Load and validate datasets
    for dataset_name in arguments.datasets_list:
        path = os.path.join(folder, f"{dataset_name}.csv")
        df = pd.read_csv(path)

        if 'District' not in df.columns:
            raise ValueError(f"'District' column missing in dataset: {dataset_name}")

        dfs.append(df)

    # Ensure all have the same columns
    first_columns = dfs[0].columns.tolist()
    for i, df in enumerate(dfs[1:], start=1):
        if df.columns.tolist() != first_columns:
            raise ValueError(f"Column mismatch in dataset: {arguments.datasets_list[i]}")

    # Ensure all have the same 'District' values (and in same order)
    base_districts = dfs[0]['District'].tolist()
    for i, df in enumerate(dfs[1:], start=1):
        if df['District'].tolist() != base_districts:
            raise ValueError(f"'District' values or order mismatch in dataset: {arguments.datasets_list[i]}")

    # Sum up datasets (excluding 'District')
    summed_df = dfs[0].copy()
    numeric_cols = [col for col in summed_df.columns if col != 'District']
    for df in dfs[1:]:
        summed_df[numeric_cols] += df[numeric_cols]

    # Write result
    output_path = os.path.join(folder, f"{arguments.new_dataset_name}.csv")
    summed_df.to_csv(output_path, index=False)

    print(f"✅ Finished sum_up_datasets: Output written to {output_path}")
