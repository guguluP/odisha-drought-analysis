"""Run ONCE (needs data/raw): makes the small Odisha district GeoJSON file for the dashboard map.

The dashboard itself never reads data/raw. This script:
1. reads the atlas district shapefile (Odisha rows only),
2. joins them to our clean lookup tables on the numeric ID (names in the atlas are corrupted, IDs are safe),
3. simplifies the outlines (fewer points = faster map), converts to longitude/latitude (EPSG:4326),
4. saves data/clean/geo/odisha_districts.geojson.

Run from the project root:  python dashboard/make_geojson.py
"""
from pathlib import Path

import geopandas as gpd
import pandas as pd
import shapely

ROOT = Path(__file__).resolve().parent.parent
SHP = ROOT / "data" / "raw" / "DroughtAtlas_v2" / "Administrative-Boundaries_Shapefile"
CLEAN = ROOT / "data" / "clean"
OUT = CLEAN / "geo"
OUT.mkdir(parents=True, exist_ok=True)

lookup_districts = pd.read_csv(CLEAN / "lookup_odisha_districts_clean.csv")  # district_id, district_name_raw, district


def prepare(gdf, tolerance_m):
    # Simplify in metres (the shapefile CRS is Lambert Conformal Conic), then convert to lon/lat and round to ~10 m
    gdf = gdf.copy()
    gdf["geometry"] = gdf.geometry.simplify(tolerance_m)
    gdf = gdf.to_crs(epsg=4326)
    gdf["geometry"] = shapely.set_precision(gdf.geometry.values, 0.0001)
    return gdf


# --- Odisha districts: join on ID
dists = gpd.read_file(SHP / "DISTRICT_BOUNDARY.shp")
dists = dists[dists["STATE"] == "ODISHA"].merge(lookup_districts, left_on="ID", right_on="district_id", how="inner")
dists = dists[["district", "geometry"]].rename(columns={"district": "name"})
dists = prepare(dists, 500)
dists.to_file(OUT / "odisha_districts.geojson", driver="GeoJSON")

print(f"odisha_districts.geojson: {(OUT / 'odisha_districts.geojson').stat().st_size / 1e6:.2f} MB")
print("Odisha districts:", len(dists))
