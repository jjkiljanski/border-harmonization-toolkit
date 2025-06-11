import pandas as pd
import os

from core.core import AdministrativeHistory
from data_models.harmonization_config import SumUpDataTablesArgs, CreateDistAreaDatasetArgs
from data_models.econ_data_metadata import DataTableMetadata

def collapse_metadata_dicts(metadata_list: list[DataTableMetadata], new_data_table_id: str) -> DataTableMetadata:
    """
    Collapses multiple DataTableMetadata objects into according to rules defined separately for every attribute.
    """
    def collapse_field(values):
        unique = set(values)
        return unique.pop() if len(unique) == 1 else "VARIES"
    
    def unique_or_none(values):
        unique = set(values)
        return unique.pop() if len(unique) == 1 else None
    
    def unique_or_error(values):
        unique = set(values)
        if len(unique) == 1:
            return unique.pop()
        else:
            raise ValueError(f"Attempted to sum up datasets {[md.data_table_id for md in metadata_list]} with incompatible metadata entries: {unique}.")
    
    def concatenate(attr_name):
        if len({getattr(md, attr_name) for md in metadata_list})<=1:
            return getattr(metadata_list[0], attr_name)
        else:
            values_to_concatenate = [f"{md.data_table_id}: {getattr(md, attr_name)}" for md in metadata_list]
            return ", ".join(values_to_concatenate)

    sample = metadata_list[0]

    return DataTableMetadata(
        data_table_id=new_data_table_id,
        category=unique_or_error([md.category for md in metadata_list]),
        source=collapse_field([md.source for md in metadata_list]),
        link=collapse_field([md.link for md in metadata_list]),
        table=None,
        page=None,
        pdf_page=None,
        description = {
            "pol": ", ".join(f"{md.data_table_id}: {md.description.get('pol', '')}" for md in metadata_list),
            "eng": ", ".join(f"{md.data_table_id}: {md.description.get('eng', '')}" for md in metadata_list),
        },
        date=collapse_field([md.date for md in metadata_list]),
        orig_adm_state_date=unique_or_error([md.adm_state_date for md in metadata_list]), # Use adm_state_date as the "original" adm. state date for the dataset.
        adm_state_date=unique_or_error([md.adm_state_date for md in metadata_list]),
        standardization_comments="Summed up from the datasets: " + ", ".join([f'{md.data_table_id} (orig_adm_state_date: {md.orig_adm_state_date})' for md in metadata_list]) + "\n" + concatenate("standardization_comments"),
        harmonization_method=concatenate("harmonization_method"),
        imputation_method=concatenate("imputation_method"),
        columns=sample.columns  # Assumes columns are the same, as validated earlier
    )


def sum_up_data_tables(administrative_history: AdministrativeHistory, arguments: SumUpDataTablesArgs) -> None:
    """
    This method loads multiple tables from CSV files, sums them up to a new data table,
    saves it, and deletes the old data tables.
    The metadata of both the datasets are collapsed to one (not implemented yet).

    This method should be applied only to harmonized datasets!
    """
    folder = administrative_history.data_harmonization_output_folder
    print(f"🟡 Starting sum_up_data_tables: {arguments.data_tables_list} -> {arguments.new_data_table_name}.csv")

    dfs = []

    # Load and validate data tables
    for data_table_name in arguments.data_tables_list:
        path = os.path.join(folder, f"{data_table_name}.csv")
        df = pd.read_csv(path)

        if 'District' not in df.columns:
            raise ValueError(f"'District' column missing in data table: {data_table_name}")

        dfs.append(df)

    # Ensure all have the same columns
    first_columns = dfs[0].columns.tolist()
    for i, df in enumerate(dfs[1:], start=1):
        if df.columns.tolist() != first_columns:
            raise ValueError(f"Column mismatch in data table: {arguments.data_tables_list[i]}")

    # Ensure all have the same 'District' values (and in same order)
    base_districts = dfs[0]['District'].tolist()
    for i, df in enumerate(dfs[1:], start=1):
        if df['District'].tolist() != base_districts:
            raise ValueError(f"'District' values or order mismatch in data table: {arguments.data_tables_list[i]}")

    # Sum up data tables (excluding 'District')
    summed_df = dfs[0].copy()
    numeric_cols = [col for col in summed_df.columns if col != 'District']
    for df in dfs[1:]:
        summed_df[numeric_cols] += df[numeric_cols]

    # Write result
    output_path = os.path.join(folder, f"{arguments.new_data_table_name}.csv")
    summed_df.to_csv(output_path, index=False)

    # Find metadata dicts of the datasets
    metadata_dicts = [metadata_dict for metadata_dict in administrative_history.harmonization_metadata if metadata_dict.data_table_id in arguments.data_tables_list]

    # Collapse metadata and update the harmonization_metadata list
    collapsed_metadata = collapse_metadata_dicts(metadata_dicts, arguments.new_data_table_name)
    administrative_history.harmonized_data_metadata = [
        md for md in administrative_history.harmonized_data_metadata
        if md.data_table_id not in arguments.data_tables_list
    ] + [collapsed_metadata]

    print(f"✅ Finished sum_up_data_tables: Output written to {output_path}")

def create_dist_area_dataset(administrative_history: AdministrativeHistory, arguments: CreateDistAreaDatasetArgs):
    """
    This method creates a data table with district areas for the administrative_history.harmonize_to_date.
    Table metadata is created on the basis of the info passed in arguments.
    
    Returns:
    - df (pd.DataFrame): DataFrame with 'District' and 'Area' columns. Area is in hectares.
    """
    print(f"🟡 Starting create_dist_area_dataset (adm. state for {administrative_history.harmonize_to_date.date()})")
    data_table_metadata = arguments.data_table_metadata
    output_path = administrative_history.data_harmonization_output_folder + data_table_metadata.data_table_id + ".csv"
    # Get the GeoDataFrame of districts
    dist_gdf = administrative_history.dist_registry._plot_layer(administrative_history.harmonize_to_date)

    # Select only homeland values
    homeland_dist_names = administrative_history.find_adm_state_by_date(administrative_history.harmonize_to_date).all_district_names(homeland_only=True)
    dist_gdf = dist_gdf[dist_gdf["name_id"].isin(homeland_dist_names)]

    # Project to a metric CRS (e.g., EPSG:3857 or any equal-area projection)
    dist_gdf_proj = dist_gdf.to_crs(epsg=3857)

    # Calculate area in square meters, then convert to hectares
    dist_gdf_proj["Area"] = dist_gdf_proj["geometry"].area / 10_000  # m² → ha

    # Create DataFrame with 'District' and 'Area'
    df = dist_gdf_proj[["name_id", "Area"]].rename(columns={"name_id": "District"})

    # Write the DataFrame to csv
    df.to_csv(output_path, index = False)

    # Update harmonized_data_metadata
    data_table_metadata.date = administrative_history.harmonize_to_date.strftime("%d.%m.%Y")
    data_table_metadata.adm_state_date = administrative_history.harmonize_to_date
    administrative_history.harmonized_data_metadata.append(data_table_metadata)

    print(f"✅ Finished create_dist_area_dataset: Metadata and output added to the database.")