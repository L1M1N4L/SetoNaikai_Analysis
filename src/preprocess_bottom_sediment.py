"""
Script 2: preprocess_bottom_sediment.py
Parses bottom_2023.xlsx: handles C_ quality flags, converts DMS coordinates,
cleans season/sea-area labels, applies physical bounds.
"""
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import numpy as np
import pandas as pd

IN  = "data/raw/benthos_data/bottom_2023.xlsx"
OUT = "data/processed/bottom_sediment_clean.csv"

print("Reading bottom_2023.xlsx …")
df = pd.read_excel(IN, sheet_name="底質_累積2023", header=0)
print(f"Raw shape: {df.shape}")
print(f"Columns: {list(df.columns)}")

# ------------------------------------------------------------------
# 1. Coordinate conversion: DMS → decimal degrees
# ------------------------------------------------------------------
df["lat_dd"] = (
    pd.to_numeric(df["緯度_度"], errors="coerce")
    + pd.to_numeric(df["緯度_分"], errors="coerce") / 60
    + pd.to_numeric(df["緯度_秒"], errors="coerce") / 3600
)
df["lon_dd"] = (
    pd.to_numeric(df["経度_度"], errors="coerce")
    + pd.to_numeric(df["経度_分"], errors="coerce") / 60
    + pd.to_numeric(df["経度_秒"], errors="coerce") / 3600
)

# Sanity check: Japan-wide bounds (includes Tokyo Bay, Ise Bay, SIS)
bad_lat = (df["lat_dd"] < 30) | (df["lat_dd"] > 46)
bad_lon = (df["lon_dd"] < 129) | (df["lon_dd"] > 145)
print(f"Coord out-of-Japan-range: lat={bad_lat.sum()}, lon={bad_lon.sum()}")

# ------------------------------------------------------------------
# 2. Season
# ------------------------------------------------------------------
df["Season"] = df["季節"].astype(str).str[0].map({"2": "Summer", "4": "Winter"})
print(f"Season value counts:\n{df['Season'].value_counts()}")

# ------------------------------------------------------------------
# 3. Sea area
# ------------------------------------------------------------------
df["sea_area"] = pd.to_numeric(df["海域コード"], errors="coerce")

# Tag region by sea_area for downstream filtering
df["study_region"] = df["sea_area"].apply(
    lambda x: "Tokyo" if x == 100
    else ("Ise" if x in [200, 201, 202] else
          ("SIS" if (pd.notna(x) and x >= 300 and x < 700) else "Other"))
)
print(f"Study region counts:\n{df['study_region'].value_counts()}")

# ------------------------------------------------------------------
# 4. Handle C_ quality flag columns
#    Measurement columns and their C_ counterparts
# ------------------------------------------------------------------
MEAS = {
    "礫分":   "C_礫分",
    "砂分":   "C_砂分",
    "粘土分": "C_粘土分",
    "pH":    "C_pH",
    "ORP":   "C_ORP",
    "乾燥減量": "C_乾燥減量",
    "強熱減量": "C_強熱減量",
    "COD":   "C_COD",
    "TN":    "C_TN",
    "TP":    "C_TP",
    "TOC":   "C_TOC",
    "硫化物": "C_硫化物",
}

for meas_col, flag_col in MEAS.items():
    if meas_col not in df.columns:
        continue
    df[meas_col] = pd.to_numeric(df[meas_col], errors="coerce")

    if flag_col not in df.columns:
        df[f"is_censored_{meas_col}"] = False
        df[f"is_estimated_{meas_col}"] = False
        continue

    flag_str = df[flag_col].astype(str).str.strip()

    # Censored = value below detection limit (< sign in flag)
    is_censored = flag_str.str.contains("<", na=False)
    df[f"is_censored_{meas_col}"] = is_censored
    # Substitute half detection limit where censored
    df.loc[is_censored, meas_col] = df.loc[is_censored, meas_col] / 2

    # Estimated = non-empty, non-"<", non-nan flag string
    is_estimated = (
        (~is_censored)
        & flag_str.notna()
        & (~flag_str.isin(["", "nan", "None", "0"]))
    )
    df[f"is_estimated_{meas_col}"] = is_estimated

# ------------------------------------------------------------------
# 5. Physical bounds for sediment variables
# ------------------------------------------------------------------
sediment_bounds = {
    "TOC":   (0, 100),
    "COD":   (0, 150),
    "TN":    (0, 20),
    "TP":    (0, 10),
    "硫化物": (0, 20),
    "ORP":  (-400, 300),
    "pH":   (5, 10),
    "強熱減量": (0, 100),
    "乾燥減量": (0, 100),
    "礫分":  (0, 100),
    "砂分":  (0, 100),
    "粘土分": (0, 100),
}
for col, (lo, hi) in sediment_bounds.items():
    if col in df.columns:
        n_lo = (df[col] < lo).sum()
        n_hi = (df[col] > hi).sum()
        if n_lo + n_hi > 0:
            print(f"  {col}: {n_lo} below {lo}, {n_hi} above {hi} → set NaN")
        df.loc[df[col] < lo, col] = np.nan
        df.loc[df[col] > hi, col] = np.nan

# ------------------------------------------------------------------
# 6. Other numeric columns
# ------------------------------------------------------------------
df["水深"] = pd.to_numeric(df["水深"], errors="coerce")
df["年"]   = pd.to_numeric(df["年"],   errors="coerce")
df["月"]   = pd.to_numeric(df["月"],   errors="coerce")

# ------------------------------------------------------------------
# 7. Select and save
# ------------------------------------------------------------------
keep = (
    ["年", "月", "Season", "lat_dd", "lon_dd", "水深", "sea_area", "study_region",
     "pH", "ORP", "乾燥減量", "強熱減量", "COD", "TN", "TP", "TOC", "硫化物",
     "礫分", "砂分", "粘土分"]
    + [c for c in df.columns if c.startswith("is_censored_") or c.startswith("is_estimated_")]
)
keep = [c for c in keep if c in df.columns]
out_df = df[keep].copy()
out_df.to_csv(OUT, index=False, encoding="utf-8-sig")

print(f"\nSaved → {OUT}")
print(f"Shape: {out_df.shape}")
print(f"Year range: {df['年'].min():.0f}–{df['年'].max():.0f}")
print(f"Sea areas: {df['sea_area'].value_counts().to_dict()}")
print(f"\nTOC summary:\n{out_df['TOC'].describe()}")
print(f"\nSulfides (硫化物) summary:\n{out_df['硫化物'].describe()}")
print(f"\nORP summary:\n{out_df['ORP'].describe()}")
print(f"\nMissing values per key column:")
for col in ["TOC", "硫化物", "ORP", "COD", "强熱減量"]:
    if col in out_df.columns:
        print(f"  {col}: {out_df[col].isna().sum()}")
