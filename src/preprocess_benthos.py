"""
Script 3: preprocess_benthos.py
Parses benthos_2023.xlsx from wide format to long format species-station
abundance table, handles overflow rows, standardises species names.
"""
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import numpy as np
import pandas as pd

IN  = "data/raw/benthos_data/benthos_2023.xlsx"
OUT = "data/processed/benthos_long.csv"

print("Reading benthos_2023.xlsx …")
# Header is on row index 1 (row 0 is a Japanese note)
df_raw = pd.read_excel(IN, sheet_name="底生生物_累積2023", header=1)
print(f"Raw shape: {df_raw.shape}")

META = ["年度", "県コード", "連番", "県番号", "調査年月日"]
all_cols = list(df_raw.columns)
print(f"First 10 cols: {all_cols[:10]}")

# ------------------------------------------------------------------
# 1. Detect overflow rows
#    Overflow = same 年度 and 連番 as the previous row
# ------------------------------------------------------------------
df_raw["is_overflow"] = (
    (df_raw["年度"] == df_raw["年度"].shift(1))
    & (df_raw["連番"] == df_raw["連番"].shift(1))
)
print(f"Overflow rows detected: {df_raw['is_overflow'].sum()}")

# ------------------------------------------------------------------
# 2. Wide → long pivot
#    Species data starts at column index 5, in groups of 4:
#    学名N (latin), 和名N (japanese), 個体数N (count), 湿重量N (wet weight g)
# ------------------------------------------------------------------
non_meta_cols = all_cols[5:]
n_groups = len(non_meta_cols) // 4
remainder = len(non_meta_cols) % 4
if remainder:
    print(f"  Warning: {remainder} trailing columns not in groups of 4 — will ignore")

print(f"Species groups per row: {n_groups}")

records = []
for row_idx, row in df_raw.iterrows():
    meta = {m: row[m] for m in META}
    meta["is_overflow"] = row["is_overflow"]

    for i in range(n_groups):
        base = 5 + i * 4
        if base + 3 >= len(all_cols):
            break
        latin_col  = all_cols[base]
        jname_col  = all_cols[base + 1]
        count_col  = all_cols[base + 2]
        weight_col = all_cols[base + 3]

        count = row[count_col]
        # Skip empty/zero entries
        if pd.isna(count):
            continue
        try:
            count_val = float(count)
        except (ValueError, TypeError):
            continue
        if count_val == 0:
            continue

        latin = str(row[latin_col]).strip() if pd.notna(row[latin_col]) else ""
        jname = str(row[jname_col]).strip() if pd.notna(row[jname_col]) else ""
        weight = row[weight_col]

        if not latin or latin in ("nan", "None", ""):
            continue

        # Weight may contain "< 0.01" style censored values
        if pd.isna(weight):
            weight_val = np.nan
        else:
            weight_str = str(weight).strip()
            if weight_str.startswith("<"):
                try:
                    weight_val = float(weight_str.replace("<", "").strip()) / 2
                except ValueError:
                    weight_val = np.nan
            else:
                try:
                    weight_val = float(weight_str)
                except ValueError:
                    weight_val = np.nan

        records.append({
            **meta,
            "学名":     latin,
            "和名":     jname,
            "個体数":   count_val,
            "湿重量_g": weight_val,
        })

long_df = pd.DataFrame(records)
print(f"\nLong format records: {len(long_df):,}")
print(f"Unique stations (連番): {long_df['連番'].nunique()}")
print(f"Unique species (学名): {long_df['学名'].nunique()}")

# ------------------------------------------------------------------
# 3. Temporal columns
# ------------------------------------------------------------------
long_df["調査年月日"] = pd.to_datetime(long_df["調査年月日"], errors="coerce")
long_df["Year"]  = long_df["調査年月日"].dt.year
long_df["Month"] = long_df["調査年月日"].dt.month
# Fix single known typo: 2109 → 2019 (年度 column is authoritative)
# Use 年度 (fiscal year) to correct any misread years
long_df["年度"] = pd.to_numeric(long_df["年度"], errors="coerce")
bad_year = long_df["Year"] > 2030
if bad_year.sum() > 0:
    print(f"Fixing {bad_year.sum()} bad year(s) using 年度 as proxy")
    long_df.loc[bad_year, "Year"] = long_df.loc[bad_year, "年度"]
    long_df.loc[bad_year, "Month"] = long_df.loc[bad_year, "Month"]  # month stays from date
long_df["Season"] = long_df["Month"].map(
    lambda m: "Summer" if m in [7, 8] else ("Winter" if m in [1, 2] else "Other")
)
print(f"\nYear range: {long_df['Year'].min():.0f}–{long_df['Year'].max():.0f}")
print(f"Season counts:\n{long_df['Season'].value_counts()}")

# ------------------------------------------------------------------
# 4. Flag rare species (< 3 occurrences across all station-surveys)
# ------------------------------------------------------------------
sp_counts = long_df["学名"].value_counts()
common = sp_counts[sp_counts >= 3].index
long_df["学名_clean"] = long_df["学名"].where(long_df["学名"].isin(common), other="Rare_sp")
print(f"\nSpecies ≥3 occurrences (kept individually): {len(common)}")
print(f"Rare species collapsed: {long_df['学名'].nunique() - len(common)}")

# ------------------------------------------------------------------
# 5. Top species
# ------------------------------------------------------------------
print(f"\nTop 15 species by occurrence:")
print(sp_counts.head(15).to_string())

# ------------------------------------------------------------------
# 6. Save
# ------------------------------------------------------------------
long_df.to_csv(OUT, index=False, encoding="utf-8-sig")
print(f"\nSaved → {OUT}")
print(f"Shape: {long_df.shape}")
