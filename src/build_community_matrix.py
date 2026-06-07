"""
Script 4: build_community_matrix.py
Pivots benthos_long.csv into station × species abundance matrices
(one per season) and computes diversity indices per station-year.
"""
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import numpy as np
import pandas as pd

IN  = "data/processed/benthos_long.csv"

print("Reading benthos_long.csv …")
df = pd.read_csv(IN, encoding="utf-8-sig")
print(f"Shape: {df.shape}")
print(f"Seasons: {df['Season'].value_counts().to_dict()}")

def shannon(row):
    vals = row[row > 0]
    if len(vals) == 0:
        return np.nan
    total = vals.sum()
    p = vals / total
    return -(p * np.log(p)).sum()

def simpson(row):
    vals = row[row > 0]
    if len(vals) == 0:
        return np.nan
    total = vals.sum()
    p = vals / total
    return 1 - (p ** 2).sum()

def margalef(row):
    vals = row[row > 0]
    S = len(vals)
    N = vals.sum()
    if S <= 1 or N <= 1:
        return np.nan
    return (S - 1) / np.log(N)

def pielou(H, S):
    if S <= 1 or np.isnan(H):
        return np.nan
    return H / np.log(S)

diversity_records = []

for season in ["Summer", "Winter"]:
    sub = df[df["Season"] == season].copy()
    if sub.empty:
        continue

    # Pivot: rows = (連番, Year), cols = 学名_clean, values = sum of 個体数
    mat = sub.pivot_table(
        index=["連番", "Year"],
        columns="学名_clean",
        values="個体数",
        aggfunc="sum",
        fill_value=0,
    )

    # Save community matrix
    out_path = f"data/processed/community_matrix_{season.lower()}.csv"
    mat.to_csv(out_path, encoding="utf-8-sig")
    print(f"\n{season} community matrix → {out_path}")
    print(f"  Shape: {mat.shape} (station-years × species)")

    # Compute diversity indices per station-year
    species_mat = mat.drop(columns=["Rare_sp"], errors="ignore")

    for idx_tuple in mat.index:
        row = species_mat.loc[idx_tuple]
        H  = shannon(row)
        Si = simpson(row)
        S  = (row > 0).sum()
        N  = row.sum()
        D  = margalef(row)
        J  = pielou(H, S)

        station, year = idx_tuple
        diversity_records.append({
            "連番":     station,
            "Year":    year,
            "Season":  season,
            "S":       S,          # species richness
            "N":       N,          # total individuals
            "Shannon": H,
            "Simpson": Si,
            "Margalef": D,
            "Pielou":  J,
        })

div_df = pd.DataFrame(diversity_records)
out_div = "data/processed/diversity_indices.csv"
div_df.to_csv(out_div, index=False, encoding="utf-8-sig")
print(f"\nDiversity indices → {out_div}")
print(f"Shape: {div_df.shape}")
print(f"\nSummer diversity summary:")
print(div_df[div_df["Season"] == "Summer"][["Shannon", "Simpson", "Margalef", "Pielou"]].describe().round(3))
print(f"\nWinter diversity summary:")
print(div_df[div_df["Season"] == "Winter"][["Shannon", "Simpson", "Margalef", "Pielou"]].describe().round(3))
