"""
Script 1: preprocess_environmental.py
Merges all YYYY_REGION_wq-raw shapefiles into a single clean
bottom-layer water quality time series CSV.
"""
import os
import glob
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import numpy as np
import pandas as pd
import shapefile
from tqdm import tqdm

RAW_ENV = "data/raw/environmental_data"
OUT = "data/processed/env_bottom_timeseries.csv"

FLOAT_COLS = [
    "do_2", "salt2", "ph2", "toc2", "tn2", "tp2", "cod2",
    "nh4n2", "no2n2", "no3n2", "po4p2", "chloroph_1", "feiochin2", "doc2"
]
META_COLS = [
    "uniqueid", "zettaicode", "locationna", "wancode", "prefectuei",
    "watercode", "renban", "nendo", "survey_ym", "surveyyear",
    "surveymont", "surveyday", "saisuipoin", "saisuidept",
    "latitude", "longitude", "dataflag", "scale"
]

frames = []
shp_paths = sorted(glob.glob(os.path.join(RAW_ENV, "*_wq-raw", "output.shp")))
print(f"Found {len(shp_paths)} shapefiles")

for shp_path in tqdm(shp_paths, desc="Reading shapefiles"):
    folder = os.path.basename(os.path.dirname(shp_path))
    parts = folder.split("_")
    year_folder = int(parts[0])
    region = parts[1]

    try:
        sf = shapefile.Reader(shp_path)
    except Exception as e:
        print(f"  SKIP {folder}: {e}")
        continue

    fields = [f[0] for f in sf.fields[1:]]
    records = sf.records()
    if not records:
        continue

    df = pd.DataFrame(records, columns=fields)
    df["region"] = region
    df["year_folder"] = year_folder
    frames.append(df)

print(f"\nConcatenating {len(frames)} frames...")
df_all = pd.concat(frames, ignore_index=True)
print(f"Total raw records: {len(df_all):,}")

# ------------------------------------------------------------------
# 1. Numeric coercions
# ------------------------------------------------------------------
df_all["wtemp"]      = pd.to_numeric(df_all["wtemp"],     errors="coerce")
df_all["saisuidept"] = pd.to_numeric(df_all["saisuidept"], errors="coerce")
df_all["saisuipoin"] = pd.to_numeric(df_all["saisuipoin"], errors="coerce")
df_all["dataflag"]   = pd.to_numeric(df_all["dataflag"],   errors="coerce").fillna(9)
df_all["scale"]      = pd.to_numeric(df_all["scale"],      errors="coerce").fillna(0)
df_all["depth"]      = pd.to_numeric(df_all["depth"],      errors="coerce")

for col in FLOAT_COLS:
    if col in df_all.columns:
        df_all[col] = pd.to_numeric(df_all[col], errors="coerce")

# ------------------------------------------------------------------
# 2. Physical bounds — set implausible values to NaN
# ------------------------------------------------------------------
bounds = {
    "do_2":   (0, 20),
    "salt2":  (0, 40),
    "wtemp":  (0, 35),
    "ph2":    (6.5, 9.5),
    "cod2":   (0, 30),
}
for col, (lo, hi) in bounds.items():
    if col in df_all.columns:
        mask_lo = df_all[col] < lo
        mask_hi = df_all[col] > hi
        df_all.loc[mask_hi, col] = np.nan
        # For DO: clamp negatives to 0 and flag, don't NaN
        if col == "do_2":
            df_all["is_near_anoxic"] = mask_lo
            df_all.loc[mask_lo, col] = 0.0
        else:
            df_all.loc[mask_lo, col] = np.nan

if "is_near_anoxic" not in df_all.columns:
    df_all["is_near_anoxic"] = False

# ------------------------------------------------------------------
# 3. Select bottom layer: highest saisuipoin per (zettaicode, survey_ym, year_folder)
#    Break ties by dataflag ASC then scale DESC (best quality first)
# ------------------------------------------------------------------
df_all = df_all.sort_values(
    ["zettaicode", "survey_ym", "year_folder", "dataflag", "scale"],
    ascending=[True, True, True, True, False]
)

# For each station+survey keep the record with max saisuipoin
group_keys = ["zettaicode", "survey_ym", "year_folder"]
idx_max = df_all.groupby(group_keys)["saisuipoin"].idxmax()
bottom = df_all.loc[idx_max].reset_index(drop=True)
print(f"Bottom-layer records after filter: {len(bottom):,}")

# ------------------------------------------------------------------
# 4. Add derived columns
# ------------------------------------------------------------------
bottom["surveyyear"] = pd.to_numeric(bottom["surveyyear"], errors="coerce")
bottom["surveymont"] = pd.to_numeric(bottom["surveymont"], errors="coerce")
bottom["Season"] = bottom["surveymont"].apply(
    lambda m: "Summer" if m in [6, 7, 8, 9]
    else ("Winter" if m in [1, 2, 3] else "Other")
)

# ------------------------------------------------------------------
# 5. Save
# ------------------------------------------------------------------
keep_cols = (
    META_COLS
    + ["wtemp", "depth", "region", "year_folder", "is_near_anoxic", "Season"]
    + [c for c in FLOAT_COLS if c in bottom.columns]
)
keep_cols = [c for c in keep_cols if c in bottom.columns]
bottom[keep_cols].to_csv(OUT, index=False, encoding="utf-8-sig")
print(f"\nSaved → {OUT}")
print(f"Shape: {bottom[keep_cols].shape}")
print(f"Year range: {bottom['surveyyear'].min():.0f}–{bottom['surveyyear'].max():.0f}")
print(f"Regions: {bottom['region'].value_counts().to_dict()}")
print(f"\nDO summary:")
print(bottom["do_2"].describe())
print(f"\nMissing DO: {bottom['do_2'].isna().sum():,} / {len(bottom):,}")
