"""
Step 4 — Mantel Tests for Community-Environment Correlation
Reproduces Figure 9 of Lai et al. (2024).

Environmental variables joined at STATION LEVEL (連番 + Year) directly
from the raw sediment data — not regional annual means.
DO joined via spatial nearest-neighbour to env_bottom_timeseries.

Inputs:
  data/processed/community_matrix_summer.csv
  data/processed/community_matrix_winter.csv
  data/processed/step3_diversity_env_joined.csv  (station-level DO)
  data/raw/benthos_data/bottom_2023.xlsx          (station-level sediment)

Outputs:
  data/processed/step4_mantel_results.csv
  data/processed/step4_station_env_summer.csv
  figures/step4_*.png
"""

import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import numpy as np
import pandas as pd
from scipy import stats
from scipy.spatial.distance import pdist, squareform
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")

os.makedirs("figures", exist_ok=True)
np.random.seed(42)

DO_NORMOXIC  = 4.0
DO_HYPOXIC   = 2.0
N_PERM       = 999
SUMMER_MONTHS = [6, 7, 8, 9]

# ─────────────────────────────────────────────
# Mantel test (Spearman, permutation)
# ─────────────────────────────────────────────
def mantel_test(dist1, dist2, n_perm=999):
    """Simple Mantel test (Spearman-based, permutation)."""
    n     = dist1.shape[0]
    idx   = np.triu_indices(n, k=1)
    d1    = dist1[idx].astype(float)
    d2    = dist2[idx].astype(float)
    mask  = ~(np.isnan(d1) | np.isnan(d2))
    d1, d2 = d1[mask], d2[mask]
    if len(d1) < 10:
        return np.nan, np.nan, len(d1)
    obs_r, _ = stats.spearmanr(d1, d2)
    perm_r   = np.empty(n_perm)
    for i in range(n_perm):
        pi       = np.random.permutation(n)
        dp       = dist1[np.ix_(pi, pi)][idx][mask]
        perm_r[i], _ = stats.spearmanr(dp, d2)
    p = (np.sum(np.abs(perm_r) >= np.abs(obs_r)) + 1) / (n_perm + 1)
    return round(float(obs_r), 4), round(float(p), 4), int(len(d1))

def partial_mantel_test(dist1, dist2, dist3, n_perm=999):
    """Partial Mantel: r(dist1, dist2 | dist3) controlling for dist3.
    Residualises both dist1 and dist2 on dist3, then Spearman-correlates.
    dist3 = geographic distance (covariate to control for).
    """
    n = dist1.shape[0]
    idx = np.triu_indices(n, k=1)
    d1 = dist1[idx].astype(float)
    d2 = dist2[idx].astype(float)
    d3 = dist3[idx].astype(float)
    mask = ~(np.isnan(d1) | np.isnan(d2) | np.isnan(d3))
    d1, d2, d3 = d1[mask], d2[mask], d3[mask]
    if len(d1) < 10:
        return np.nan, np.nan, len(d1)
    # Residualise d1 and d2 on d3 (linear regression)
    from numpy.linalg import lstsq
    X = np.column_stack([np.ones(len(d3)), d3])
    d1_res = d1 - X @ lstsq(X, d1, rcond=None)[0]
    d2_res = d2 - X @ lstsq(X, d2, rcond=None)[0]
    obs_r, _ = stats.spearmanr(d1_res, d2_res)
    # Permutation test: permute rows/cols of dist1 (not the flat residuals)
    perm_r = np.empty(n_perm)
    for i in range(n_perm):
        pi = np.random.permutation(n)
        dp = dist1[np.ix_(pi, pi)][idx][mask]
        dp_res = dp - X @ lstsq(X, dp, rcond=None)[0]
        perm_r[i], _ = stats.spearmanr(dp_res, d2_res)
    p = (np.sum(np.abs(perm_r) >= np.abs(obs_r)) + 1) / (n_perm + 1)
    return round(float(obs_r), 4), round(float(p), 4), int(len(d1))

# ─────────────────────────────────────────────
# 4A. Build station-level environmental lookup
# ─────────────────────────────────────────────
print("=" * 60)
print("4A. Building station-level environmental data")
print("=" * 60)

# --- Sediment variables (TOC, sulfides, ORP, COD, LOI, clay) ---
sed_raw = pd.read_excel(
    "data/raw/benthos_data/bottom_2023.xlsx",
    sheet_name="底質_累積2023", header=0
)
for col in ["連番","年","月"]:
    sed_raw[col] = pd.to_numeric(sed_raw[col], errors="coerce")
sed_raw["Season"] = sed_raw["月"].apply(
    lambda m: "Summer" if m in [7,8] else ("Winter" if m in [1,2] else "Other")
)
for col in ["TOC","硫化物","ORP","COD","強熱減量","粘土分","水深"]:
    sed_raw[col] = pd.to_numeric(sed_raw[col], errors="coerce")

# Apply same physical bounds as preprocessing
sed_raw.loc[sed_raw["ORP"] >  300, "ORP"] = np.nan
sed_raw.loc[sed_raw["ORP"] < -400, "ORP"] = np.nan
sed_raw.loc[sed_raw["TOC"]  < 0,   "TOC"] = np.nan
sed_raw.loc[sed_raw["硫化物"] < 0,  "硫化物"] = np.nan

SED_VARS = ["TOC", "硫化物", "ORP", "COD", "強熱減量", "粘土分", "水深"]
sed_station = (sed_raw[sed_raw["Season"].isin(["Summer","Winter"])]
               .groupby(["連番","年","Season"])[SED_VARS]
               .mean()
               .reset_index()
               .rename(columns={"年":"Year"}))

print(f"Sediment station-year records: {len(sed_station)}")
print(f"Unique stations: {sed_station['連番'].nunique()}")

# Station coordinates for geographic distance matrix
def dms_to_dd(row, deg_col, min_col, sec_col):
    deg = pd.to_numeric(row[deg_col], errors="coerce")
    mn  = pd.to_numeric(row[min_col], errors="coerce")
    sec = pd.to_numeric(row[sec_col], errors="coerce")
    return deg + mn/60 + sec/3600

sed_raw["lat_dd"] = sed_raw.apply(lambda r: dms_to_dd(r,"緯度_度","緯度_分","緯度_秒"), axis=1)
sed_raw["lon_dd"] = sed_raw.apply(lambda r: dms_to_dd(r,"経度_度","経度_分","経度_秒"), axis=1)

station_geo = (sed_raw.dropna(subset=["連番","lat_dd","lon_dd"])
               .groupby("連番")
               .agg(lat_dd=("lat_dd","first"), lon_dd=("lon_dd","first"))
               .reset_index())
print(f"Station coordinates available: {len(station_geo)}")

# --- DO: from step3 joined data (station-level spatial NN) ---
div_env = pd.read_csv("data/processed/step3_diversity_env_joined.csv")
div_env["連番"] = pd.to_numeric(div_env["連番"], errors="coerce")
div_env["Year"]  = pd.to_numeric(div_env["Year"],  errors="coerce")

do_lookup = div_env[["連番","Year","Season","do_station"]].dropna(subset=["do_station"])
print(f"DO lookup records: {len(do_lookup)}")

# ─────────────────────────────────────────────
# 4B. Mantel tests per season
# ─────────────────────────────────────────────
results  = []
ENV_VARS = {
    "DO":         "do_station",
    "TOC":        "TOC",
    "Sulfides":   "硫化物",
    "ORP":        "ORP",
    "COD":        "COD",
    "LOI":        "強熱減量",
    "Clay%":      "粘土分",
}

for season in ["Summer", "Winter"]:
    print(f"\n{'='*55}")
    print(f"Season: {season}")
    print(f"{'='*55}")

    mat = pd.read_csv(
        f"data/processed/community_matrix_{season.lower()}.csv",
        encoding="utf-8-sig", index_col=[0, 1]
    )
    mat.index.names = ["連番", "Year"]
    n = mat.shape[0]
    print(f"Community matrix: {n} station-years × {mat.shape[1]} species")

    # Bray-Curtis on relative abundances
    vals      = np.nan_to_num(mat.values.astype(float), nan=0.0)
    row_sums  = vals.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1
    rel       = vals / row_sums
    bc_mat    = squareform(pdist(rel, metric="braycurtis"))
    print(f"Mean Bray-Curtis dissimilarity: {bc_mat[np.triu_indices(n,k=1)].mean():.3f}")

    # Build env data frame aligned to community matrix row order
    # 連番 may be string codes (e.g. 'Afk-1') for non-sediment stations
    mat_idx = pd.DataFrame(
        [(i[0], i[1]) for i in mat.index],
        columns=["連番", "Year"]
    )
    mat_idx["renban_num"] = pd.to_numeric(mat_idx["連番"], errors="coerce")
    mat_idx["Year"]       = pd.to_numeric(mat_idx["Year"],    errors="coerce")

    # DO join — match on numeric 連番 (step3 stores them as floats)
    do_seas = do_lookup[do_lookup["Season"] == season].copy()
    do_seas["renban_num"] = pd.to_numeric(do_seas["連番"], errors="coerce")
    env_df = mat_idx.merge(
        do_seas[["renban_num","Year","do_station"]],
        on=["renban_num","Year"], how="left"
    )

    # Sediment join uses numeric 連番 only
    sed_seas = sed_station[sed_station["Season"] == season].copy()
    sed_seas["renban_num"] = sed_seas["連番"].astype(float)
    env_df = env_df.merge(
        sed_seas[["renban_num","Year"] + SED_VARS],
        on=["renban_num","Year"], how="left"
    )
    env_df.columns = (env_df.columns
                      .str.replace("硫化物", "Sulfides")
                      .str.replace("強熱減量", "LOI")
                      .str.replace("粘土分", "Clay_pct")
                      .str.replace("水深", "Depth_m"))

    col_map = {
        "DO":       "do_station",
        "TOC":      "TOC",
        "Sulfides": "Sulfides",
        "ORP":      "ORP",
        "COD":      "COD",
        "LOI":      "LOI",
        "Clay%":    "Clay_pct",
    }

    n_env  = env_df["do_station"].notna().sum()
    n_sed  = env_df["TOC"].notna().sum()
    print(f"DO matched:      {n_env} / {n} station-years")
    print(f"Sediment matched: {n_sed} / {n} station-years")

    if season == "Summer":
        env_df.to_csv("data/processed/step4_station_env_summer.csv", index=False)

    # ── ALL stations ──
    print(f"\n  {'Variable':10s}  {'n_pairs':>8s}  {'Mantel r':>10s}  {'p-value':>10s}")
    for var_name, col in col_map.items():
        if col not in env_df.columns:
            continue
        vals_e = env_df[col].values.astype(float)
        valid  = ~np.isnan(vals_e)
        n_valid = valid.sum()
        if n_valid < 20:
            print(f"  {var_name:10s}  {n_valid:>8d}  {'–':>10s}  {'–':>10s}  (insufficient)")
            continue
        # Impute mean for distance calc, keep only fully valid pairs
        vals_imp = vals_e.copy()
        vals_imp[~valid] = np.nanmean(vals_e)
        env_dist = squareform(pdist(vals_imp.reshape(-1,1), metric="euclidean"))
        # Zero-out pairs where either row is missing
        miss_mask = ~valid
        env_dist[miss_mask, :] = np.nan
        env_dist[:, miss_mask] = np.nan

        r, p, n_pairs = mantel_test(bc_mat, env_dist, N_PERM)
        sig = "***" if p<0.001 else ("**" if p<0.01 else ("*" if p<0.05 else "ns"))
        print(f"  {var_name:10s}  {n_pairs:>8d}  {r:>10.4f}  {p:>10.4f}  {sig}")
        results.append({
            "Season": season, "Subset": "All", "Variable": var_name,
            "n_stations": int(n_valid), "n_pairs": n_pairs,
            "Mantel_r": r, "p_value": p, "Significance": sig
        })

    # ── STRESSED stations (DO ≤ 4) ──
    stressed = env_df["do_station"].fillna(999) <= DO_NORMOXIC
    n_str = stressed.sum()
    if n_str >= 20:
        bc_str = bc_mat[np.ix_(stressed.values, stressed.values)]
        env_str = env_df[stressed].reset_index(drop=True)
        print(f"\n  Stressed stations (DO≤4, n={n_str}):")
        print(f"  {'Variable':10s}  {'n_pairs':>8s}  {'Mantel r':>10s}  {'p-value':>10s}")
        for var_name, col in col_map.items():
            if col not in env_str.columns:
                continue
            vals_e = env_str[col].values.astype(float)
            valid  = ~np.isnan(vals_e)
            if valid.sum() < 10:
                continue
            vals_imp = vals_e.copy()
            vals_imp[~valid] = np.nanmean(vals_e)
            env_dist = squareform(pdist(vals_imp.reshape(-1,1), metric="euclidean"))
            env_dist[~valid, :] = np.nan
            env_dist[:, ~valid] = np.nan
            r, p, n_pairs = mantel_test(bc_str, env_dist, N_PERM)
            sig = "***" if p<0.001 else ("**" if p<0.01 else ("*" if p<0.05 else "ns"))
            print(f"  {var_name:10s}  {n_pairs:>8d}  {r:>10.4f}  {p:>10.4f}  {sig}")
            results.append({
                "Season": season, "Subset": f"Stressed(DO≤4,n={n_str})",
                "Variable": var_name, "n_stations": int(valid.sum()),
                "n_pairs": n_pairs, "Mantel_r": r, "p_value": p, "Significance": sig
            })
    else:
        print(f"\n  Stressed subset: n={n_str} — insufficient for Mantel")

    # ── PARTIAL MANTEL (Summer only): BC ~ Env | Geographic distance ──
    if season == "Summer":
        print(f"\n  --- Partial Mantel (Summer): controlling for geographic distance ---")
        # Build geographic distance matrix aligned to mat row order
        coords = mat_idx.merge(station_geo[["連番","lat_dd","lon_dd"]].rename(
            columns={"連番":"renban_num"}),
            left_on="renban_num", right_on="renban_num", how="left"
        )
        lat = coords["lat_dd"].values.astype(float)
        lon = coords["lon_dd"].values.astype(float)
        # Haversine geo_mat
        R = 6371.0
        geo_mat = np.zeros((n, n))
        for i in range(n):
            if np.isnan(lat[i]) or np.isnan(lon[i]):
                geo_mat[i, :] = np.nan
                geo_mat[:, i] = np.nan
                continue
            dlat = np.radians(lat - lat[i])
            dlon = np.radians(lon - lon[i])
            a = np.sin(dlat/2)**2 + np.cos(np.radians(lat[i])) * np.cos(np.radians(lat)) * np.sin(dlon/2)**2
            geo_mat[i, :] = 2 * R * np.arcsin(np.sqrt(np.clip(a, 0, 1)))

        has_geo = ~np.isnan(geo_mat[0])
        geo_coverage = has_geo.sum()
        print(f"  Geographic distances available for {geo_coverage}/{n} stations")

        partial_results = []
        print(f"  {'Variable':10s}  {'Simple r':>10s}  {'Partial r':>10s}  {'Partial p':>10s}")
        for var_name, col in col_map.items():
            if col not in env_df.columns:
                continue
            vals_e = env_df[col].values.astype(float)
            valid = ~np.isnan(vals_e)
            if valid.sum() < 20:
                continue
            vals_imp = vals_e.copy()
            vals_imp[~valid] = np.nanmean(vals_e)
            env_dist = squareform(pdist(vals_imp.reshape(-1,1), metric="euclidean"))
            env_dist[~valid, :] = np.nan
            env_dist[:, ~valid] = np.nan

            # Simple r (already computed above — just grab from results)
            simple_rows = [r for r in results if r["Season"]==season and r["Subset"]=="All" and r["Variable"]==var_name]
            simple_r = simple_rows[0]["Mantel_r"] if simple_rows else np.nan

            p_r, p_p, p_n = partial_mantel_test(bc_mat, env_dist, geo_mat, n_perm=N_PERM)
            sig = "***" if p_p<0.001 else ("**" if p_p<0.01 else ("*" if p_p<0.05 else "ns"))
            print(f"  {var_name:10s}  {simple_r:>10.4f}  {p_r:>10.4f}  {p_p:>10.4f}  {sig}")
            partial_results.append({
                "Season": season, "Variable": var_name, "Simple_r": simple_r,
                "Partial_r": p_r, "Partial_p": p_p, "Partial_sig": sig,
                "n_pairs": p_n
            })
        partial_df = pd.DataFrame(partial_results)
        partial_df.to_csv("data/processed/step4_partial_mantel.csv", index=False)

results_df = pd.DataFrame(results)
results_df.to_csv("data/processed/step4_mantel_results.csv", index=False)

print("\n" + "=" * 60)
print("Full results table:")
print("=" * 60)
print(results_df[["Season","Subset","Variable","n_stations","Mantel_r","p_value","Significance"]]
      .to_string(index=False))

# ─────────────────────────────────────────────
# FIGURES
# ─────────────────────────────────────────────
print("\nGenerating figures …")

VAR_ORDER  = ["DO", "TOC", "Sulfides", "ORP", "COD", "LOI", "Clay%"]
SUBSET_ALL = "All"
COLOURS    = {"All": "#2166ac", "Stressed": "#d73027"}

fig, axes = plt.subplots(1, 2, figsize=(16, 6))
fig.suptitle(
    "Mantel Test: Bray-Curtis Dissimilarity vs Environmental Distance\n"
    "(Spearman-based, 999 permutations)",
    fontweight="bold", fontsize=12
)

for ax, season in zip(axes, ["Summer", "Winter"]):
    sub = results_df[results_df["Season"] == season]
    subsets_present = sub["Subset"].unique()

    x      = np.arange(len(VAR_ORDER))
    n_sub  = len(subsets_present)
    width  = 0.7 / n_sub

    for si, subset in enumerate(subsets_present):
        ss    = sub[sub["Subset"] == subset].set_index("Variable")
        rs    = np.array([ss.loc[v, "Mantel_r"] if v in ss.index else np.nan for v in VAR_ORDER])
        ps    = np.array([ss.loc[v, "p_value"]  if v in ss.index else np.nan for v in VAR_ORDER])
        ns    = np.array([int(ss.loc[v, "n_stations"]) if v in ss.index else 0 for v in VAR_ORDER])
        col   = "#2166ac" if "All" in subset else "#d73027"
        lbl   = "All stations" if "All" in subset else f"DO-stressed"
        offx  = (si - (n_sub-1)/2) * width

        bars = ax.bar(x + offx, rs, width, label=lbl,
                      color=col, alpha=0.85, edgecolor="k", lw=0.5)

        for bar, r, p, n_st in zip(bars, rs, ps, ns):
            if np.isnan(r):
                ax.text(bar.get_x() + bar.get_width()/2,
                        0.005, "–", ha="center", va="bottom",
                        fontsize=9, color="grey")
                continue
            sig = "***" if p<0.001 else ("**" if p<0.01 else ("*" if p<0.05 else ""))
            ypos = r + 0.005 if r >= 0 else r - 0.012
            ax.text(bar.get_x() + bar.get_width()/2, ypos,
                    sig if sig else "ns",
                    ha="center", va="bottom", fontsize=8, fontweight="bold")
            # n label at bar base
            ax.text(bar.get_x() + bar.get_width()/2,
                    0.002 if r >= 0 else r - 0.022,
                    f"n={n_st}", ha="center", va="bottom",
                    fontsize=6, color="white" if abs(r)>0.03 else "black")

    ax.axhline(0, color="k", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(VAR_ORDER, fontsize=10)
    ax.set_ylabel("Mantel r (Spearman)", fontsize=10)
    ax.set_title(f"{season}", fontweight="bold", fontsize=11)
    ax.legend(fontsize=9)
    ax.set_ylim(-0.12, 0.25)
    ax.yaxis.grid(True, alpha=0.3, linestyle="--")
    ax.set_axisbelow(True)

plt.tight_layout()
plt.savefig("figures/step4_mantel_results.png", dpi=150, bbox_inches="tight")
plt.close()
print("  → figures/step4_mantel_results.png")

# Fig 2 — Correlation between environmental variables at matched stations
env_summer = pd.read_csv("data/processed/step4_station_env_summer.csv")
env_plot = env_summer[["do_station","TOC","Sulfides","ORP","COD","LOI"]].dropna()

fig, axes = plt.subplots(2, 3, figsize=(15, 9))
fig.suptitle("Pairwise Environmental Variable Relationships\n(Summer station-level data)",
             fontweight="bold")

pairs = [
    ("do_station", "TOC",       "Bottom DO (mg/L)",   "TOC (mg/g)"),
    ("do_station", "Sulfides",  "Bottom DO (mg/L)",   "Sulfides (mg/g)"),
    ("do_station", "ORP",       "Bottom DO (mg/L)",   "ORP (mV)"),
    ("TOC",        "Sulfides",  "TOC (mg/g)",         "Sulfides (mg/g)"),
    ("TOC",        "ORP",       "TOC (mg/g)",         "ORP (mV)"),
    ("Sulfides",   "ORP",       "Sulfides (mg/g)",    "ORP (mV)"),
]

for ax, (x_col, y_col, xl, yl) in zip(axes.flatten(), pairs):
    sub = env_summer[[x_col, y_col]].dropna()
    ax.scatter(sub[x_col], sub[y_col], alpha=0.4, s=15,
               color="#4575b4", edgecolors="none")
    if len(sub) >= 5:
        slope, intercept, r, p, _ = stats.linregress(sub[x_col], sub[y_col])
        xr = np.linspace(sub[x_col].min(), sub[x_col].max(), 100)
        ax.plot(xr, slope*xr + intercept, "r-", lw=1.5, alpha=0.8)
        sig = "***" if p<0.001 else ("**" if p<0.01 else ("*" if p<0.05 else "ns"))
        r_sp, p_sp = stats.spearmanr(sub[x_col], sub[y_col])
        ax.text(0.05, 0.93, f"r={r_sp:.2f}{sig}  n={len(sub)}",
                transform=ax.transAxes, fontsize=8,
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8))
    ax.set_xlabel(xl, fontsize=9)
    ax.set_ylabel(yl, fontsize=9)
    ax.set_title(f"{xl.split('(')[0].strip()} vs {yl.split('(')[0].strip()}",
                 fontweight="bold", fontsize=9)

plt.tight_layout()
plt.savefig("figures/step4_env_pairplots.png", dpi=150, bbox_inches="tight")
plt.close()
print("  → figures/step4_env_pairplots.png")

# Fig 3 — Partial vs Simple Mantel comparison (Summer)
try:
    partial_df = pd.read_csv("data/processed/step4_partial_mantel.csv")
    if len(partial_df) > 0:
        fig, ax = plt.subplots(figsize=(10, 5))
        fig.suptitle(
            "Simple vs Partial Mantel r (Summer, controlling for geographic distance)\n"
            "Partial Mantel isolates pure environmental signal from spatial autocorrelation",
            fontweight="bold", fontsize=10)

        vars_p = partial_df["Variable"].tolist()
        x = np.arange(len(vars_p))
        w = 0.35
        bars_s = ax.bar(x - w/2, partial_df["Simple_r"], w,
                        label="Simple Mantel r", color="#2166ac", alpha=0.8,
                        edgecolor="k", lw=0.5)
        bars_p = ax.bar(x + w/2, partial_df["Partial_r"], w,
                        label="Partial Mantel r (| geo dist)", color="#d73027", alpha=0.8,
                        edgecolor="k", lw=0.5, hatch="//")

        for bar, r, sig in zip(bars_s, partial_df["Simple_r"],
                                [results_df[(results_df["Season"]=="Summer") &
                                            (results_df["Subset"]=="All") &
                                            (results_df["Variable"]==v)]["Significance"].values[0]
                                 if len(results_df[(results_df["Season"]=="Summer") &
                                                   (results_df["Subset"]=="All") &
                                                   (results_df["Variable"]==v)]) > 0 else ""
                                 for v in vars_p]):
            if not np.isnan(r):
                ax.text(bar.get_x()+bar.get_width()/2, r+0.004, sig,
                        ha="center", fontsize=8, fontweight="bold")

        for bar, r, sig in zip(bars_p, partial_df["Partial_r"], partial_df["Partial_sig"]):
            if not np.isnan(r):
                ax.text(bar.get_x()+bar.get_width()/2, r+0.004, sig,
                        ha="center", fontsize=8, fontweight="bold")

        ax.axhline(0, color="k", lw=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(vars_p, fontsize=10)
        ax.set_ylabel("Mantel r (Spearman)", fontsize=10)
        ax.legend(fontsize=9)
        ax.yaxis.grid(True, alpha=0.3, ls="--")
        ax.set_axisbelow(True)
        ax.text(0.02, 0.97,
                "Bars remaining significant after geographic control\n"
                "= pure environmental signal (not just spatial proximity)",
                transform=ax.transAxes, fontsize=8, va="top",
                bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.9))
        plt.tight_layout()
        plt.savefig("figures/step4_partial_mantel.png", dpi=150, bbox_inches="tight")
        plt.close()
        print("  → figures/step4_partial_mantel.png")
except Exception as e:
    print(f"  Partial Mantel figure skipped: {e}")

print("\n" + "=" * 60)
print("Step 4 COMPLETE")
print("=" * 60)
