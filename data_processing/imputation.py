import pandas as pd
from datetime import datetime
import geopandas as gpd
from shapely.ops import nearest_points
from shapely.geometry import Point
from typing import List

from core.core import AdministrativeHistory
from data_models.adm_unit import DistrictRegistry

def take_from_closest_centroid(
        administrative_history: AdministrativeHistory,
        df: pd.DataFrame,
        adm_state_date: datetime,
        numeric_cols: List[str],
        data_completeness_threshold=0.2
    ) -> pd.DataFrame:
    # Step 1: Get the GeoDataFrame of districts and compute centroids
    gdf = administrative_history.dist_registry.gdf(adm_state_date).copy()
    gdf["centroid"] = gdf.geometry.centroid

    # Step 2: Merge centroids into df by District
    df_with_centroids = df.merge(
        gdf[["District", "centroid"]],
        on="District",
        how="left"
    )

    # Step 3: Convert to GeoDataFrame for spatial calculations
    df_with_centroids = gpd.GeoDataFrame(df_with_centroids, geometry="centroid", crs=gdf.crs)

    # Step 4: Loop through each column (except 'District' and 'centroid') and impute selectively
    columns_to_impute = [
        col for col in numeric_cols
        if col != "District" and df[col].isna().mean() < data_completeness_threshold
    ]

    for col in columns_to_impute:
        unknown = df_with_centroids[df_with_centroids[col].isna()]
        known = df_with_centroids[df_with_centroids[col].notna()]

        for idx, row in unknown.iterrows():
            distances = known["centroid"].distance(row["centroid"])
            nearest_idx = distances.idxmin()
            df_with_centroids.at[idx, col] = known.at[nearest_idx, col]

    # Step 5: Clean up and return
    df_with_centroids = df_with_centroids.drop(columns="centroid")
    return pd.DataFrame(df_with_centroids)