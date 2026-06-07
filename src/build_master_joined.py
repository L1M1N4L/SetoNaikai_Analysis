"""
Script 5: build_master_joined.py
Spatial nearest-neighbour join: sediment records → environmental DO.
Produces master_sediment_env.csv for Random Forest modelling.
"""
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import numpy as np
import pandas as pd

ENV_PATH = "data/processed/env_bottom_timeseries.csv"
SED_PATH = "data/processed/bottom_sediment_clean.csv"
OUT      = "data/processed/master_sediment_env.csv"

print("Loading datasets …")
env = pd.read_csv(ENV_PATH, encoding="utf-8-sig")
sed = pd.read_csv(SED_PATH, encoding="utf-8-sig")

print(f"ENV records: {len(env):,}  |  SED records: {len(sed):,}")

# ------------------------------------------------------------------
# 1. Harmonise season labels
# ------------------------------------------------------------------
# ENV Season already: Summer/Winter/Other (months 6-9 = Summer, 1-3 = Winter)
# SED Season: Summer (month 7-8), Winter (month 1-2)
# For join we align: SED Summer → ENV Summer, SED Winter → ENV Winter

env["Year"]   = pd.to_numeric(env["surveyyear"], errors="coerce")
env["Month"]  = pd.to_numeric(env["surveymont"], errors="coerce")
sed["Year"]   = pd.to_numeric(sed["年"], errors="coerce")
sed["Month"]  = pd.to_numeric(sed["月"], errors="coerce")

# ------------------------------------------------------------------
# 2. Haversine distance function (vectorised)
# ------------------------------------------------------------------
def haversine_km(lat1, lon1, lat2, lon2):
    """
    lat1/lon1: arrays of reference points (env stations)
    lat2/lon2: scalars or arrays of query points (sed stations)
    Returns distance matrix: shape (len(lat2), len(lat1))
    """
    R = 6371.0
    lat1r = np.radians(lat1)
    lat2r = np.radians(lat2)
    dlat  = lat2r[:, None] - lat1r[None, :]
    dlon  = np.radians(lon2[:, None] - lon1[None, :])
    a = (np.sin(dlat / 2) ** 2
         + np.cos(lat1r) * np.cos(lat2r[:, None]) * np.sin(dlon / 2) ** 2)
    return 2 * R * np.arcsin(np.sqrt(a))

# ------------------------------------------------------------------
# 3. Nearest-neighbour join per year-season
# ------------------------------------------------------------------
joined_rows = []

for season in ["Summer", "Winter"]:
    sed_s = sed[sed["Season"] == season].copy()
    env_s = env[env["Season"] == season].copy()

    years = sed_s["Year"].dropna().unique()
    print(f"\n{season}: {len(sed_s)} sediment rows, {len(env_s)} env rows, {len(years)} years")

    for year in sorted(years):
        s_yr = sed_s[sed_s["Year"] == year].copy()
        e_yr = env_s[env_s["Year"] == year].copy()

        # Fallback: if no env data for exact year, use ±2 year window
        if e_yr.empty:
            e_yr = env_s[
                (env_s["Year"] >= year - 2) & (env_s["Year"] <= year + 2)
            ].copy()
        if e_yr.empty:
            print(f"  {year}: no env data within ±2 years — skipping {len(s_yr)} records")
            continue

        # Drop env rows with missing lat/lon or DO
        e_yr = e_yr.dropna(subset=["latitude", "longitude", "do_2"])
        if e_yr.empty:
            continue

        # Compute distances
        dist_mat = haversine_km(
            e_yr["latitude"].values, e_yr["longitude"].values,
            s_yr["lat_dd"].values,  s_yr["lon_dd"].values,
        )

        # For each sediment row, find nearest env station
        nearest_idx = dist_mat.argmin(axis=1)
        dist_min    = dist_mat.min(axis=1)

        matched = e_yr.iloc[nearest_idx].reset_index(drop=True)

        s_yr = s_yr.reset_index(drop=True)
        s_yr["do_nearest"]       = matched["do_2"].values
        s_yr["wtemp_nearest"]    = matched["wtemp"].values
        s_yr["salt_nearest"]     = matched["salt2"].values
        s_yr["env_zettaicode"]   = matched["zettaicode"].values
        s_yr["env_dist_km"]      = dist_min
        s_yr["env_year_matched"] = matched["Year"].values

        joined_rows.append(s_yr)

master = pd.concat(joined_rows, ignore_index=True)

# ------------------------------------------------------------------
# 4. Quality flags
# ------------------------------------------------------------------
master["env_join_suspect"] = master["env_dist_km"] > 20

# Binary hypoxia label from matched DO
master["is_hypoxic"] = master["do_nearest"] <= 2.0

print(f"\nMaster table: {len(master):,} rows")
print(f"Suspect joins (>20 km): {master['env_join_suspect'].sum()} ({master['env_join_suspect'].mean()*100:.1f}%)")
print(f"Hypoxic labels (DO≤2): {master['is_hypoxic'].sum()} ({master['is_hypoxic'].mean()*100:.1f}%)")
print(f"Year range: {master['Year'].min():.0f}–{master['Year'].max():.0f}")
print(f"\nDO distribution at matched env stations:")
print(master["do_nearest"].describe())
print(f"\nTop sea areas:")
print(master["sea_area"].value_counts().head(8))

# ------------------------------------------------------------------
# 5. Save
# ------------------------------------------------------------------
master.to_csv(OUT, index=False, encoding="utf-8-sig")
print(f"\nSaved → {OUT}")
print(f"Columns: {list(master.columns)}")
