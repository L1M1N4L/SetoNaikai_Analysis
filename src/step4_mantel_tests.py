"""
Step 4 — Mantel Tests for Community-Environment Correlation
Reproduces Figure 9 of Lai et al. (2024).

Computes Bray-Curtis dissimilarity between station pairs from the
community abundance matrix, and Euclidean distance matrices for
environmental variables, then runs Spearman-based Mantel tests
with 999 permutations.

Inputs:
  data/processed/community_matrix_summer.csv
  data/processed/community_matrix_winter.csv
  data/processed/step3_diversity_env_joined.csv

Outputs:
  data/processed/step4_mantel_results.csv
  data/processed/step4_bray_curtis_summer.csv
  figures/step4_*.png
"""

import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import numpy as np
import pandas as pd
from scipy import stats
from scipy.spatial.distance import pdist, squareform, braycurtis
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")

os.makedirs("figures", exist_ok=True)
np.random.seed(42)

DO_HYPOXIC  = 2.0
DO_NORMOXIC = 4.0
N_PERM      = 999

# ─────────────────────────────────────────────
# Mantel test implementation
# ─────────────────────────────────────────────
def mantel_test(dist1, dist2, n_perm=999):
    """
    Spearman-based Mantel test.
    dist1, dist2: symmetric square distance matrices (numpy arrays).
    Returns: r (Spearman r on upper triangle), p-value (permutation).
    """
    n = dist1.shape[0]
    idx = np.triu_indices(n, k=1)
    d1 = dist1[idx]
    d2 = dist2[idx]
    mask = ~(np.isnan(d1) | np.isnan(d2))
    d1, d2 = d1[mask], d2[mask]
    if len(d1) < 10:
        return np.nan, np.nan, 0

    obs_r, _ = stats.spearmanr(d1, d2)

    # Permutation test: permute rows/cols of dist1
    perm_r = np.zeros(n_perm)
    for i in range(n_perm):
        perm_idx = np.random.permutation(n)
        d1p = dist1[np.ix_(perm_idx, perm_idx)][idx]
        d1p = d1p[mask]
        perm_r[i], _ = stats.spearmanr(d1p, d2)

    p_val = (np.sum(np.abs(perm_r) >= np.abs(obs_r)) + 1) / (n_perm + 1)
    return round(float(obs_r), 4), round(float(p_val), 4), len(d1)

# ─────────────────────────────────────────────
# 4A. Load community matrices and env data
# ─────────────────────────────────────────────
print("=" * 60)
print("4A. Loading community matrices")
print("=" * 60)

results = []

for season in ["Summer", "Winter"]:
    print(f"\n{'='*50}")
    print(f"Season: {season}")
    print(f"{'='*50}")

    mat = pd.read_csv(
        f"data/processed/community_matrix_{season.lower()}.csv",
        encoding="utf-8-sig", index_col=[0,1]
    )
    print(f"Community matrix: {mat.shape}")

    # Station-years as rows; relative abundance (proportions)
    mat_vals = mat.values.astype(float)
    mat_vals = np.nan_to_num(mat_vals, nan=0.0)
    row_sums = mat_vals.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1
    mat_rel = mat_vals / row_sums

    # ─── Bray-Curtis dissimilarity matrix ───
    print("Computing Bray-Curtis dissimilarity …")
    n = mat_rel.shape[0]
    bc_flat = pdist(mat_rel, metric="braycurtis")
    bc_mat  = squareform(bc_flat)
    print(f"BC matrix: {bc_mat.shape}  |  mean BC = {bc_flat.mean():.3f}")

    if season == "Summer":
        bc_df = pd.DataFrame(bc_mat, index=mat.index, columns=mat.index)
        bc_df.to_csv("data/processed/step4_bray_curtis_summer.csv")

    # ─── Environmental distance matrices from step3 joined data ───
    div_env = pd.read_csv("data/processed/step3_diversity_env_joined.csv")
    div_env["連番"] = pd.to_numeric(div_env["連番"], errors="coerce")
    div_env["Year"] = pd.to_numeric(div_env["Year"], errors="coerce")

    # Match env values to the community matrix row order (連番, Year)
    mat_index = pd.DataFrame(mat.index.tolist(), columns=["連番","Year"])
    mat_index["連番"] = pd.to_numeric(mat_index["連番"], errors="coerce")
    mat_index["Year"] = pd.to_numeric(mat_index["Year"], errors="coerce")

    # Select available env columns dynamically
    env_cols_needed = ["連番","Year","do_station","mean_TOC","mean_sulfide","mean_ORP","mean_COD"]
    env_cols_avail  = [c for c in env_cols_needed if c in div_env.columns]
    env_matched = mat_index.merge(
        div_env[div_env["Season"]==season][env_cols_avail],
        on=["連番","Year"], how="left"
    )
    # Add any missing sediment columns as NaN
    for c in ["mean_TOC","mean_sulfide","mean_ORP","mean_COD"]:
        if c not in env_matched.columns:
            env_matched[c] = np.nan
    print(f"Env data matched to {env_matched['do_station'].notna().sum()} / {n} rows")

    ENV_VARS = {
        "DO":       "do_station",
        "TOC":      "mean_TOC",
        "Sulfides": "mean_sulfide",
        "ORP":      "mean_ORP",
        "COD":      "mean_COD",
    }

    # ─── Run Mantel tests — ALL station-years ───
    print(f"\nMantel tests — {season} ALL stations (n={n}):")
    print(f"  {'Variable':12s}  {'Mantel r':>10s}  {'p-value':>10s}  {'n_pairs':>8s}")
    for var_name, col in ENV_VARS.items():
        env_vals = env_matched[col].values.astype(float)
        # Euclidean distance matrix for env variable
        valid = ~np.isnan(env_vals)
        if valid.sum() < 20:
            print(f"  {var_name:12s}  {'–':>10s}  {'–':>10s}  {valid.sum():>8d}")
            continue
        env_sub = env_vals.copy()
        env_sub[~valid] = np.nanmean(env_vals)  # impute mean for distance calc
        env_dist = squareform(pdist(env_sub.reshape(-1,1), metric="euclidean"))

        r, p, n_pairs = mantel_test(bc_mat, env_dist, N_PERM)
        sig = "***" if p<0.001 else ("**" if p<0.01 else ("*" if p<0.05 else "ns"))
        print(f"  {var_name:12s}  {r:>10.4f}  {p:>10.4f} {sig}  {n_pairs:>8d}")
        results.append({
            "Season": season, "Subset": "All",
            "Variable": var_name, "Mantel_r": r, "p_value": p,
            "Significance": sig, "n_pairs": n_pairs
        })

    # ─── Run Mantel tests — STRESSED station-years (DO ≤ 4) ───
    stressed_mask = env_matched["do_station"].fillna(999) <= DO_NORMOXIC
    n_str = stressed_mask.sum()
    if n_str >= 20:
        bc_str = bc_mat[np.ix_(stressed_mask.values, stressed_mask.values)]
        env_str = env_matched[stressed_mask]
        print(f"\nMantel tests — {season} STRESSED stations (DO≤4, n={n_str}):")
        print(f"  {'Variable':12s}  {'Mantel r':>10s}  {'p-value':>10s}  {'n_pairs':>8s}")
        for var_name, col in ENV_VARS.items():
            env_vals = env_str[col].values.astype(float)
            valid = ~np.isnan(env_vals)
            if valid.sum() < 10:
                continue
            env_sub = env_vals.copy()
            env_sub[~valid] = np.nanmean(env_vals)
            env_dist = squareform(pdist(env_sub.reshape(-1,1), metric="euclidean"))
            r, p, n_pairs = mantel_test(bc_str, env_dist, N_PERM)
            sig = "***" if p<0.001 else ("**" if p<0.01 else ("*" if p<0.05 else "ns"))
            print(f"  {var_name:12s}  {r:>10.4f}  {p:>10.4f} {sig}  {n_pairs:>8d}")
            results.append({
                "Season": season, "Subset": "Stressed(DO≤4)",
                "Variable": var_name, "Mantel_r": r, "p_value": p,
                "Significance": sig, "n_pairs": n_pairs
            })
    else:
        print(f"  Insufficient stressed records (n={n_str}) — skipping")

# ─────────────────────────────────────────────
# Save results
# ─────────────────────────────────────────────
results_df = pd.DataFrame(results)
results_df.to_csv("data/processed/step4_mantel_results.csv", index=False)

print("\n" + "=" * 60)
print("Full Mantel results table:")
print("=" * 60)
print(results_df.to_string(index=False))

# ─────────────────────────────────────────────
# FIGURES
# ─────────────────────────────────────────────
print("\nGenerating figures …")

# Fig 1 — Mantel results bar chart
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle("Mantel Test Results: Community Dissimilarity vs Environmental Distance\n"
             "(Spearman-based, 999 permutations)", fontweight="bold")

seasons = ["Summer", "Winter"]
subsets = ["All", "Stressed(DO≤4)"]
colors  = {"All": "#4575b4", "Stressed(DO≤4)": "#d73027"}

for ax, season in zip(axes, seasons):
    sub = results_df[results_df["Season"] == season]
    vars_order = ["DO", "TOC", "Sulfides", "ORP", "COD"]
    x = np.arange(len(vars_order))
    width = 0.35

    for i, subset in enumerate(subsets):
        ss = sub[sub["Subset"] == subset].set_index("Variable")
        rs = [ss.loc[v, "Mantel_r"] if v in ss.index else np.nan for v in vars_order]
        ps = [ss.loc[v, "p_value"]  if v in ss.index else np.nan for v in vars_order]
        bars = ax.bar(x + i*width - width/2, rs, width,
                      label=subset, color=colors[subset], alpha=0.8,
                      edgecolor="k", lw=0.5)
        for bar, p in zip(bars, ps):
            if not np.isnan(p):
                sig = "***" if p<0.001 else ("**" if p<0.01 else ("*" if p<0.05 else ""))
                if sig:
                    ax.text(bar.get_x() + bar.get_width()/2,
                            bar.get_height() + 0.005,
                            sig, ha="center", va="bottom", fontsize=9, fontweight="bold")

    ax.axhline(0, color="k", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(vars_order, fontsize=10)
    ax.set_ylabel("Mantel r")
    ax.set_title(f"{season}", fontweight="bold")
    ax.legend(fontsize=9)
    ax.set_ylim(-0.15, 0.20)

plt.tight_layout()
plt.savefig("figures/step4_mantel_results.png", dpi=150, bbox_inches="tight")
plt.close()
print("  → figures/step4_mantel_results.png")

# Fig 2 — Bray-Curtis heatmap (summer, subset of stations)
bc_df = pd.read_csv("data/processed/step4_bray_curtis_summer.csv",
                    index_col=[0,1], header=[0,1])
# Show subset of first 40 station-years for readability
n_show = min(40, bc_df.shape[0])
bc_sub = bc_df.iloc[:n_show, :n_show].values.astype(float)

fig, ax = plt.subplots(figsize=(10, 8))
im = ax.imshow(bc_sub, cmap="YlOrRd", vmin=0, vmax=1, aspect="auto")
plt.colorbar(im, ax=ax, label="Bray-Curtis dissimilarity")
ax.set_title(f"Bray-Curtis Dissimilarity — Summer Community\n"
             f"(first {n_show} station-year pairs shown)", fontweight="bold")
ax.set_xlabel("Station-year index")
ax.set_ylabel("Station-year index")
plt.tight_layout()
plt.savefig("figures/step4_bray_curtis_heatmap.png", dpi=150, bbox_inches="tight")
plt.close()
print("  → figures/step4_bray_curtis_heatmap.png")

print("\n" + "=" * 60)
print("Step 4 COMPLETE")
print("=" * 60)
