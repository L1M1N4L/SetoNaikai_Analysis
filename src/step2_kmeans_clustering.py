"""
Step 2 — K-Means Clustering for Site Regime Classification
Replaces NMDS/PERMANOVA with validated unsupervised ML.

Inputs:
  data/processed/step1_hiroshima_bottom.csv
  data/processed/step1_osaka_bottom.csv
  data/processed/master_sediment_env.csv

Outputs:
  data/processed/step2_hiroshima_clustered.csv
  data/processed/step2_osaka_clustered.csv
  data/processed/step2_cluster_centroids.csv
  data/processed/step2_kmeans_scores.csv
  figures/step2_*.png
"""

import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import warnings
warnings.filterwarnings("ignore")

os.makedirs("figures", exist_ok=True)

SUMMER_MONTHS = [6, 7, 8, 9]
DO_HYPOXIC    = 2.0
DO_NORMOXIC   = 4.0
RANDOM_STATE  = 42

# ─────────────────────────────────────────────
# 2A. Build feature matrix — Hiroshima
# ─────────────────────────────────────────────
print("=" * 60)
print("2A. Feature matrix — Hiroshima 2014")
print("=" * 60)

hiro = pd.read_csv("data/processed/step1_hiroshima_bottom.csv")

# Cyclic month encoding
hiro["month_sin"] = np.sin(2 * np.pi * hiro["Month"] / 12)
hiro["month_cos"] = np.cos(2 * np.pi * hiro["Month"] / 12)
hiro["is_summer"] = hiro["Month"].isin(SUMMER_MONTHS).astype(int)

FEAT_HIRO = ["DO", "Temperature", "Salinity", "Strat_index",
             "month_sin", "month_cos"]

# Drop rows with any missing feature
hiro_feat = hiro.dropna(subset=FEAT_HIRO).copy()
print(f"Records with complete features: {len(hiro_feat)}")

X_raw = hiro_feat[FEAT_HIRO].values
scaler = StandardScaler()
X_sc   = scaler.fit_transform(X_raw)

# ─────────────────────────────────────────────
# 2B. K selection — elbow + silhouette
# ─────────────────────────────────────────────
print("\n2B. K selection (K = 2–6)")
K_range  = range(2, 7)
inertias = []
sil_scores = []

for k in K_range:
    km = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=20)
    labels = km.fit_predict(X_sc)
    inertias.append(km.inertia_)
    sil = silhouette_score(X_sc, labels)
    sil_scores.append(sil)
    print(f"  K={k}: inertia={km.inertia_:.1f}  silhouette={sil:.4f}")

best_k = list(K_range)[np.argmax(sil_scores)]
print(f"\nBest K by silhouette: {best_k}")

# ─────────────────────────────────────────────
# 2C. Final clustering with best K
# ─────────────────────────────────────────────
print(f"\n2C. Final K-means (K={best_k})")

km_final = KMeans(n_clusters=best_k, random_state=RANDOM_STATE, n_init=50)
hiro_feat = hiro_feat.copy()
hiro_feat["cluster"] = km_final.fit_predict(X_sc)

# Label clusters by mean DO (lowest DO = cluster 0)
centroid_do = hiro_feat.groupby("cluster")["DO"].mean().sort_values()
cluster_map  = {old: new for new, old in enumerate(centroid_do.index)}
hiro_feat["cluster"] = hiro_feat["cluster"].map(cluster_map)

# Re-order centroids accordingly
centroids_raw = scaler.inverse_transform(km_final.cluster_centers_)
centroid_df   = pd.DataFrame(centroids_raw, columns=FEAT_HIRO)
centroid_df["cluster"] = range(best_k)
centroid_df = centroid_df.set_index("cluster").reindex(
    sorted(centroid_df["cluster"])
)

print("\nCluster centroids (unstandardised):")
print(centroid_df.round(3).to_string())

# Cross-tabulate with hypoxia flag
hiro_feat["is_hypoxic"] = (hiro_feat["DO"] <= DO_HYPOXIC).astype(int)
xtab = pd.crosstab(
    hiro_feat["cluster"], hiro_feat["is_hypoxic"],
    rownames=["cluster"], colnames=["is_hypoxic (DO≤2)"],
    margins=True
)
print(f"\nCross-tabulation: cluster × hypoxia flag")
print(xtab.to_string())

# Per-cluster summary
print("\nPer-cluster DO summary:")
print(hiro_feat.groupby("cluster")[["DO","Temperature","Salinity","Strat_index"]]\
      .mean().round(3).to_string())

# Save
hiro_feat.to_csv("data/processed/step2_hiroshima_clustered.csv", index=False)
centroid_df.to_csv("data/processed/step2_cluster_centroids.csv")

# ─────────────────────────────────────────────
# 2D. Osaka clustering (no DO — use stratification features)
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("2D. K-means — Osaka 2016 (stratification-based)")
print("=" * 60)

osaka = pd.read_csv("data/processed/step1_osaka_bottom.csv")
osaka["month_sin"] = np.sin(2 * np.pi * osaka["Month"] / 12)
osaka["month_cos"] = np.cos(2 * np.pi * osaka["Month"] / 12)

FEAT_OSA = ["Temperature", "Salinity", "Strat_index",
            "Nominal_Depth_m", "month_sin", "month_cos"]

osa_feat = osaka.dropna(subset=FEAT_OSA).copy()
print(f"Records with complete features: {len(osa_feat)}")

X_osa = StandardScaler().fit_transform(osa_feat[FEAT_OSA].values)

sil_osa = []
for k in K_range:
    km = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=20)
    labels = km.fit_predict(X_osa)
    sil_osa.append(silhouette_score(X_osa, labels))
    print(f"  K={k}: silhouette={sil_osa[-1]:.4f}")

best_k_osa = list(K_range)[np.argmax(sil_osa)]
print(f"Best K: {best_k_osa}")

km_osa = KMeans(n_clusters=best_k_osa, random_state=RANDOM_STATE, n_init=50)
osa_feat = osa_feat.copy()
osa_feat["cluster"] = km_osa.fit_predict(X_osa)

# Label by mean stratification
cent_strat = osa_feat.groupby("cluster")["Strat_index"].mean().sort_values(ascending=False)
osa_map    = {old: new for new, old in enumerate(cent_strat.index)}
osa_feat["cluster"] = osa_feat["cluster"].map(osa_map)
osa_feat["high_strat"] = (osa_feat["Strat_index"] > 3.0).astype(int)

print("\nOsaka cluster × high stratification:")
print(pd.crosstab(osa_feat["cluster"], osa_feat["high_strat"],
                  rownames=["cluster"], colnames=["ΔT>3°C"], margins=True))

print("\nOsaka per-cluster means:")
print(osa_feat.groupby("cluster")[["Temperature","Salinity","Strat_index","Nominal_Depth_m"]]\
      .mean().round(3).to_string())

osa_feat.to_csv("data/processed/step2_osaka_clustered.csv", index=False)

# ─────────────────────────────────────────────
# 2E. Sediment-env master — clustering for RF label validation
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("2E. K-means on master sediment-env table (summer SIS)")
print("=" * 60)

master = pd.read_csv("data/processed/master_sediment_env.csv", encoding="utf-8-sig")
sis_sum = master[
    (master["study_region"] == "SIS") &
    (master["Season"] == "Summer")
].copy()
print(f"SIS summer sediment records: {len(sis_sum)}")

FEAT_SED = ["TOC", "硫化物", "ORP", "COD", "強熱減量", "粘土分", "水深"]
sed_feat = sis_sum.dropna(subset=FEAT_SED + ["do_nearest"]).copy()
print(f"Complete records: {len(sed_feat)}")

X_sed = StandardScaler().fit_transform(sed_feat[FEAT_SED].values)
sil_sed = []
for k in K_range:
    km = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=20)
    labels = km.fit_predict(X_sed)
    sil_sed.append(silhouette_score(X_sed, labels))
    print(f"  K={k}: silhouette={sil_sed[-1]:.4f}")

best_k_sed = list(K_range)[np.argmax(sil_sed)]
print(f"Best K: {best_k_sed}")

km_sed = KMeans(n_clusters=best_k_sed, random_state=RANDOM_STATE, n_init=50)
sed_feat = sed_feat.copy()
sed_feat["cluster"] = km_sed.fit_predict(X_sed)

cent_do = sed_feat.groupby("cluster")["do_nearest"].mean().sort_values()
sed_map  = {old: new for new, old in enumerate(cent_do.index)}
sed_feat["cluster"] = sed_feat["cluster"].map(sed_map)

print("\nSediment cluster × hypoxia flag:")
print(pd.crosstab(sed_feat["cluster"], sed_feat["is_hypoxic"],
                  rownames=["cluster"], colnames=["hypoxic(DO≤2)"], margins=True))
print("\nSediment cluster means (key variables):")
print(sed_feat.groupby("cluster")[["do_nearest","TOC","硫化物","ORP","COD"]]\
      .mean().round(3).to_string())

# Save scores table
scores_df = pd.DataFrame({
    "K": list(K_range),
    "silhouette_hiroshima": sil_scores,
    "silhouette_osaka":     sil_osa,
    "silhouette_sediment":  sil_sed,
})
scores_df.to_csv("data/processed/step2_kmeans_scores.csv", index=False)

# ─────────────────────────────────────────────
# FIGURES
# ─────────────────────────────────────────────
print("\nGenerating figures …")

# Fig 1 — Elbow + silhouette curves
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

axes[0].plot(list(K_range), inertias, "bo-", lw=2, markersize=8)
axes[0].set_xlabel("Number of clusters K")
axes[0].set_ylabel("Within-cluster sum of squares (Inertia)")
axes[0].set_title("Elbow Plot — Hiroshima K-Means", fontweight="bold")
axes[0].axvline(best_k, color="r", linestyle="--", label=f"Selected K={best_k}")
axes[0].legend()

colors_sil = {"Hiroshima": "#2166ac", "Osaka": "#d73027", "Sediment (SIS)": "#4dac26"}
for label, scores in zip(colors_sil, [sil_scores, sil_osa, sil_sed]):
    axes[1].plot(list(K_range), scores, "o-", lw=2,
                 color=colors_sil[label], label=label)
axes[1].set_xlabel("Number of clusters K")
axes[1].set_ylabel("Average Silhouette Score")
axes[1].set_title("Silhouette Scores by Dataset", fontweight="bold")
axes[1].legend()
axes[1].axhline(0, color="k", lw=0.5)

plt.tight_layout()
plt.savefig("figures/step2_elbow_silhouette.png", dpi=150, bbox_inches="tight")
plt.close()
print("  → figures/step2_elbow_silhouette.png")

# Fig 2 — Cluster scatter: DO vs Temperature vs Strat_index (Hiroshima)
cluster_colors = {0: "#d73027", 1: "#fee090", 2: "#4575b4", 3: "#313695"}
cluster_labels = {0: "Hypoxic/warm", 1: "Transitional", 2: "Normoxic/cool"}

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

for c in sorted(hiro_feat["cluster"].unique()):
    sub = hiro_feat[hiro_feat["cluster"] == c]
    col = cluster_colors.get(c, "#888888")
    lbl = cluster_labels.get(c, f"Cluster {c}")
    axes[0].scatter(sub["Temperature"], sub["DO"], c=col,
                    label=lbl, alpha=0.7, edgecolors="k", lw=0.3, s=50)

axes[0].axhline(DO_HYPOXIC, color="k", linestyle="--", lw=1, label="DO=2 mg/L (hypoxic)")
axes[0].axhline(DO_NORMOXIC, color="k", linestyle=":", lw=1, label="DO=4 mg/L (normoxic)")
axes[0].set_xlabel("Bottom Temperature (°C)")
axes[0].set_ylabel("Bottom DO (mg/L)")
axes[0].set_title(f"K-Means Clusters (K={best_k}): DO vs Temperature\nHiroshima 2014",
                  fontweight="bold")
axes[0].legend(fontsize=8)

for c in sorted(hiro_feat["cluster"].unique()):
    sub = hiro_feat[hiro_feat["cluster"] == c]
    col = cluster_colors.get(c, "#888888")
    lbl = cluster_labels.get(c, f"Cluster {c}")
    axes[1].scatter(sub["Strat_index"], sub["DO"], c=col,
                    label=lbl, alpha=0.7, edgecolors="k", lw=0.3, s=50)

axes[1].axhline(DO_HYPOXIC, color="k", linestyle="--", lw=1)
axes[1].axvline(3.0, color="grey", linestyle=":", lw=1,
                label="ΔT=3°C (strong thermocline)")
axes[1].set_xlabel("Stratification Index ΔT (°C)")
axes[1].set_ylabel("Bottom DO (mg/L)")
axes[1].set_title(f"K-Means Clusters: DO vs Stratification\nHiroshima 2014",
                  fontweight="bold")
axes[1].legend(fontsize=8)

plt.tight_layout()
plt.savefig("figures/step2_cluster_scatter_hiroshima.png", dpi=150, bbox_inches="tight")
plt.close()
print("  → figures/step2_cluster_scatter_hiroshima.png")

# Fig 3 — Sediment cluster: TOC vs Sulfides, coloured by DO
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

sc = axes[0].scatter(
    sed_feat["TOC"], sed_feat["硫化物"],
    c=sed_feat["do_nearest"], cmap="RdYlBu",
    vmin=0, vmax=10, alpha=0.7, edgecolors="k", lw=0.3, s=40
)
plt.colorbar(sc, ax=axes[0], label="Matched bottom DO (mg/L)")
axes[0].set_xlabel("TOC (mg/g)")
axes[0].set_ylabel("Sulfides (mg/g)")
axes[0].set_title("SIS Summer Sediment: TOC vs Sulfides\n(colour = matched bottom DO)",
                  fontweight="bold")

for c in sorted(sed_feat["cluster"].unique()):
    sub = sed_feat[sed_feat["cluster"] == c]
    col = cluster_colors.get(c, "#888888")
    axes[1].scatter(sub["TOC"], sub["硫化物"], c=col,
                    label=f"Cluster {c} (mean DO={sub['do_nearest'].mean():.1f})",
                    alpha=0.7, edgecolors="k", lw=0.3, s=40)
axes[1].set_xlabel("TOC (mg/g)")
axes[1].set_ylabel("Sulfides (mg/g)")
axes[1].set_title(f"SIS Summer Sediment K-Means Clusters (K={best_k_sed})",
                  fontweight="bold")
axes[1].legend(fontsize=8)

plt.tight_layout()
plt.savefig("figures/step2_sediment_cluster_scatter.png", dpi=150, bbox_inches="tight")
plt.close()
print("  → figures/step2_sediment_cluster_scatter.png")

print("\n" + "=" * 60)
print("Step 2 COMPLETE")
print("=" * 60)
print(f"  Hiroshima best K: {best_k}  (silhouette={max(sil_scores):.4f})")
print(f"  Osaka best K:     {best_k_osa}  (silhouette={max(sil_osa):.4f})")
print(f"  Sediment best K:  {best_k_sed}  (silhouette={max(sil_sed):.4f})")
