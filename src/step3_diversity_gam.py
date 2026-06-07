"""
Step 3 — Benthic Diversity Indices and GAM Analysis
Reproduces Figures 6 and 7 of Lai et al. (2024).

Joins benthos station diversity to station-level bottom DO via:
  1. 連番 coordinate lookup from sediment survey (37 exact matches)
  2. Haversine nearest-neighbour for remaining benthos stations
  Then fits GAMs (or LOWESS) of each diversity index vs bottom DO.

Inputs:
  data/processed/diversity_indices.csv
  data/processed/env_bottom_timeseries.csv
  data/raw/benthos_data/bottom_2023.xlsx   (for station coords)

Outputs:
  data/processed/step3_diversity_env_joined.csv
  data/processed/step3_spearman_heatmap_all.csv
  data/processed/step3_spearman_heatmap_hypoxic.csv
  data/processed/step3_gam_results.csv
  figures/step3_*.png
"""

import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")

try:
    from pygam import LinearGAM, s
    HAS_GAM = True
except ImportError:
    HAS_GAM = False
    print("WARNING: pygam not found — falling back to LOWESS smoother")

os.makedirs("figures", exist_ok=True)

DO_HYPOXIC   = 2.0
DO_NORMOXIC  = 4.0
SUMMER_MONTHS = [6, 7, 8, 9]
DIVERSITY_INDICES = ["Shannon", "Simpson", "Margalef", "Pielou"]

# ─────────────────────────────────────────────
# 3A. Build station coordinate lookup
# ─────────────────────────────────────────────
print("=" * 60)
print("3A. Building benthos station coordinate lookup")
print("=" * 60)

sed_raw = pd.read_excel(
    "data/raw/benthos_data/bottom_2023.xlsx",
    sheet_name="底質_累積2023", header=0
)
sed_raw["連番"] = pd.to_numeric(sed_raw["連番"], errors="coerce")
sed_raw["lat_dd"] = (
    pd.to_numeric(sed_raw["緯度_度"], errors="coerce")
    + pd.to_numeric(sed_raw["緯度_分"], errors="coerce") / 60
    + pd.to_numeric(sed_raw["緯度_秒"], errors="coerce") / 3600
)
sed_raw["lon_dd"] = (
    pd.to_numeric(sed_raw["経度_度"], errors="coerce")
    + pd.to_numeric(sed_raw["経度_分"], errors="coerce") / 60
    + pd.to_numeric(sed_raw["経度_秒"], errors="coerce") / 3600
)
sed_raw["sea_area"] = pd.to_numeric(sed_raw["海域コード"], errors="coerce")

# Station lookup: 連番 → (lat, lon, sea_area)
station_coords = (
    sed_raw.dropna(subset=["連番", "lat_dd", "lon_dd"])
    .groupby("連番")
    .agg(lat_dd=("lat_dd","first"), lon_dd=("lon_dd","first"),
         sea_area=("sea_area","first"))
    .reset_index()
)
print(f"Station coords from sediment: {len(station_coords)} stations")

# ─────────────────────────────────────────────
# 3B. Spatial nearest-neighbour join:
#     benthos station → env bottom DO
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("3B. Joining benthos diversity to station-level bottom DO")
print("=" * 60)

div  = pd.read_csv("data/processed/diversity_indices.csv", encoding="utf-8-sig")
env  = pd.read_csv("data/processed/env_bottom_timeseries.csv", encoding="utf-8-sig")

div["連番"] = pd.to_numeric(div["連番"], errors="coerce")
env["Year"]  = pd.to_numeric(env["surveyyear"], errors="coerce")
env["Month"] = pd.to_numeric(env["surveymont"], errors="coerce")
env["Season"] = env["Month"].apply(
    lambda m: "Summer" if m in SUMMER_MONTHS else ("Winter" if m in [1,2,3] else "Other")
)

# Attach coords to diversity records
div_with_coords = div.merge(station_coords, on="連番", how="left")
print(f"Diversity records with coords: {div_with_coords['lat_dd'].notna().sum()} "
      f"/ {len(div_with_coords)}")

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = np.radians(np.array(lat2) - np.array(lat1))
    dlon = np.radians(np.array(lon2) - np.array(lon1))
    a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon/2)**2
    return 2 * R * np.arcsin(np.sqrt(a))

joined_rows = []
for season in ["Summer", "Winter"]:
    div_s = div_with_coords[div_with_coords["Season"] == season].copy()
    env_s = env[(env["Season"] == season) & env["do_2"].notna()].copy()

    for year in sorted(div_s["Year"].dropna().unique()):
        d_yr = div_s[div_s["Year"] == year].copy()
        e_yr = env_s[env_s["Year"] == year].copy()
        if e_yr.empty:
            e_yr = env_s[(env_s["Year"] >= year-2) & (env_s["Year"] <= year+2)].copy()
        if e_yr.empty:
            continue

        for _, row in d_yr.iterrows():
            if pd.isna(row["lat_dd"]) or pd.isna(row["lon_dd"]):
                # No coords — use regional mean DO
                do_val  = e_yr["do_2"].mean()
                dist_km = np.nan
                env_code = "regional_mean"
            else:
                dists = haversine_km(
                    e_yr["latitude"].values, e_yr["longitude"].values,
                    np.full(len(e_yr), row["lat_dd"]),
                    np.full(len(e_yr), row["lon_dd"])
                )
                nearest_i = np.argmin(dists)
                do_val   = e_yr.iloc[nearest_i]["do_2"]
                dist_km  = dists[nearest_i]
                env_code = e_yr.iloc[nearest_i]["zettaicode"]

            joined_rows.append({
                **row.to_dict(),
                "do_station": do_val,
                "env_dist_km": dist_km,
                "env_zettaicode": env_code,
            })

div_env = pd.DataFrame(joined_rows)
div_env["is_hypoxic_station"] = div_env["do_station"] <= DO_HYPOXIC
div_env["is_stressed_station"] = div_env["do_station"] <= DO_NORMOXIC

print(f"\nJoined records: {len(div_env)}")
print(f"DO available: {div_env['do_station'].notna().sum()}")
print(f"Station DO ≤2 (hypoxic): {div_env['is_hypoxic_station'].sum()} "
      f"({div_env['is_hypoxic_station'].mean()*100:.1f}%)")
print(f"Station DO ≤4 (stressed): {div_env['is_stressed_station'].sum()} "
      f"({div_env['is_stressed_station'].mean()*100:.1f}%)")
print(f"\nStation-level DO summary:")
print(div_env["do_station"].describe().round(3))

div_env.to_csv("data/processed/step3_diversity_env_joined.csv", index=False)

# ─────────────────────────────────────────────
# 3C. Sediment variables annual mean for join
# ─────────────────────────────────────────────
master = pd.read_csv("data/processed/master_sediment_env.csv", encoding="utf-8-sig")
sed_ann = (master
           .groupby(["Year","Season"])
           .agg(mean_TOC=("TOC","mean"),
                mean_sulfide=("硫化物","mean"),
                mean_ORP=("ORP","mean"),
                mean_COD=("COD","mean"))
           .reset_index())
div_env = div_env.merge(sed_ann, on=["Year","Season"], how="left")

# ─────────────────────────────────────────────
# 3D. Spearman correlations
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("3D. Spearman correlations")
print("=" * 60)

ENV_VARS = ["do_station", "mean_TOC", "mean_sulfide", "mean_ORP", "mean_COD"]
ENV_LABELS = {
    "do_station":   "Bottom DO",
    "mean_TOC":     "TOC",
    "mean_sulfide": "Sulfides",
    "mean_ORP":     "ORP",
    "mean_COD":     "COD",
}

def spearman_matrix(df, div_cols, env_cols):
    rows = []
    for d in div_cols:
        for e in env_cols:
            sub = df[[d, e]].dropna()
            if len(sub) < 5:
                rows.append({"Diversity": d, "EnvVar": e, "r": np.nan, "p": np.nan, "n": len(sub)})
                continue
            r, p = stats.spearmanr(sub[d], sub[e])
            rows.append({"Diversity": d, "EnvVar": e,
                         "r": round(r,3), "p": round(p,4), "n": len(sub)})
    return pd.DataFrame(rows)

# All records
sub_all = div_env.dropna(subset=["do_station"])
spear_all = spearman_matrix(sub_all, DIVERSITY_INDICES, ENV_VARS)
print("\nAll stations:")
print(spear_all.pivot(index="Diversity", columns="EnvVar", values="r").round(3).to_string())

# Stressed records (DO ≤ 4)
sub_str = div_env[div_env["is_stressed_station"]].copy()
spear_str = spearman_matrix(sub_str, DIVERSITY_INDICES, ENV_VARS)
print(f"\nStressed stations (DO≤4, n={len(sub_str)}):")
print(spear_str.pivot(index="Diversity", columns="EnvVar", values="r").round(3).to_string())

# Hypoxic only (DO ≤ 2)
sub_hyp = div_env[div_env["is_hypoxic_station"]].copy()
spear_hyp = spearman_matrix(sub_hyp, DIVERSITY_INDICES, ENV_VARS)
print(f"\nHypoxic stations (DO≤2, n={len(sub_hyp)}):")
if len(sub_hyp) > 0:
    print(spear_hyp.pivot(index="Diversity", columns="EnvVar", values="r").round(3).to_string())

spear_all.to_csv("data/processed/step3_spearman_heatmap_all.csv", index=False)
spear_str.to_csv("data/processed/step3_spearman_heatmap_hypoxic.csv", index=False)

# ─────────────────────────────────────────────
# 3D2. Within-bay Spearman: Shannon/Pielou vs DO per bay
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("3D2. Within-bay Spearman: diversity vs DO")
print("=" * 60)

# Assign bay label from lat/lon bounding boxes
def assign_bay(lat, lon):
    if pd.isna(lat) or pd.isna(lon):
        return "Unknown"
    if 34.0 <= lat <= 34.55 and 131.8 <= lon <= 132.75:
        return "Hiroshima Bay"
    if 34.25 <= lat <= 34.75 and 135.0 <= lon <= 135.55:
        return "Osaka Bay"
    if 34.5 <= lat <= 35.1 and 136.4 <= lon <= 137.25:
        return "Ise Bay"
    if 33.5 <= lat <= 35.0 and 130.0 <= lon <= 134.5:
        return "SIS (other)"
    return "Other/Unknown"

div_env["bay_label"] = [assign_bay(lat, lon)
                         for lat, lon in zip(div_env["lat_dd"], div_env["lon_dd"])]

print("\nRecords per bay:")
print(div_env["bay_label"].value_counts().to_string())

# Run Spearman per bay for Shannon and Pielou vs DO
TARGET_DIVS = ["Shannon", "Pielou"]
bay_rows = []
for bay in ["Hiroshima Bay", "Osaka Bay", "Ise Bay", "SIS (other)"]:
    sub_bay = div_env[div_env["bay_label"] == bay].dropna(subset=["do_station"])
    sub_bay_str = sub_bay[sub_bay["do_station"] <= DO_NORMOXIC]
    for label, df in [("All", sub_bay), ("Stressed(DO≤4)", sub_bay_str)]:
        for div_col in TARGET_DIVS:
            sub = df[[div_col, "do_station"]].dropna()
            if len(sub) < 8:
                print(f"  SKIP {bay} [{label}] {div_col}: n={len(sub)}")
                continue
            r, p = stats.spearmanr(sub[div_col], sub["do_station"])
            sig = "***" if p<0.001 else ("**" if p<0.01 else ("*" if p<0.05 else "ns"))
            print(f"  {bay:18s}  [{label:15s}]  {div_col:8s}: r={r:+.3f}  p={p:.4f}  {sig}  n={len(sub)}")
            bay_rows.append({
                "Bay": bay, "Subset": label, "DiversityIndex": div_col,
                "Spearman_r": round(r, 3), "p_value": round(p, 4),
                "Significance": sig, "n": len(sub)
            })

bay_spear_df = pd.DataFrame(bay_rows)
bay_spear_df.to_csv("data/processed/step3_within_bay_spearman.csv", index=False)

# ─────────────────────────────────────────────
# 3E. GAM fitting
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("3E. GAM fitting")
print("=" * 60)

gam_results = []
for subset_label, subset_df in [("all", sub_all), ("stressed(DO≤4)", sub_str)]:
    for div_col in DIVERSITY_INDICES:
        sub = subset_df[[div_col, "do_station"]].dropna()
        if len(sub) < 8:
            print(f"  SKIP {div_col} [{subset_label}]: n={len(sub)}")
            continue
        r, p = stats.spearmanr(sub["do_station"], sub[div_col])
        if HAS_GAM:
            try:
                gam = LinearGAM(s(0, n_splines=5)).fit(
                    sub["do_station"].values.reshape(-1,1), sub[div_col].values)
                r2 = gam.statistics_["pseudo_r2"]["McFadden"]
                method = "GAM"
            except Exception:
                sl, ic, lr, lp, _ = stats.linregress(sub["do_station"], sub[div_col])
                r2, method = lr**2, "Linear-fallback"
        else:
            sl, ic, lr, lp, _ = stats.linregress(sub["do_station"], sub[div_col])
            r2, method = lr**2, "Linear"

        gam_results.append({
            "Subset": subset_label, "DiversityIndex": div_col,
            "n": len(sub), "Spearman_r": round(r,3), "Spearman_p": round(p,4),
            "R2": round(float(r2),3), "Method": method
        })
        print(f"  [{subset_label:16s}]  {div_col:10s}  r={r:.3f}  p={p:.4f}  R²={float(r2):.3f}")

gam_df = pd.DataFrame(gam_results)
gam_df.to_csv("data/processed/step3_gam_results.csv", index=False)

# ─────────────────────────────────────────────
# FIGURES
# ─────────────────────────────────────────────
print("\nGenerating figures …")

# Fig 1 — GAM plots: diversity vs station-level DO
# Two rows: all stations (flat/confounded) + stressed only (signal present)
fig, axes = plt.subplots(2, 4, figsize=(18, 10))
fig.suptitle(
    "Diversity Indices vs Station-Level Bottom DO\n"
    "Top row: all stations — relationship flat/confounded by spatial noise  |  "
    "Bottom row: DO-stressed subset (DO≤4) — ecologically interpretable signal",
    fontweight="bold", fontsize=10)

STRESS_COLOURS = {
    "All stations":    ("#4575b4", "#d73027", 0.30),  # scatter, fit, alpha
    "Stressed (DO≤4)": ("#2ca25f", "#006d2c", 0.45),
}

for col_i, div_col in enumerate(DIVERSITY_INDICES):
    for row_i, (label, subset) in enumerate([
        ("All stations", sub_all),
        ("Stressed (DO≤4)", sub_str)
    ]):
        ax = axes[row_i][col_i]
        sub = subset[["do_station", div_col]].dropna()

        # Background shading for hypoxia zones
        ax.axvspan(0, DO_HYPOXIC,  alpha=0.08, color="red",    label="Hypoxic" if col_i==0 else "")
        ax.axvspan(DO_HYPOXIC, DO_NORMOXIC, alpha=0.05, color="orange", label="Stressed" if col_i==0 else "")

        if len(sub) < 4:
            ax.text(0.5, 0.5, f"n={len(sub)}\nInsufficient",
                    ha="center", va="center", transform=ax.transAxes, fontsize=9)
            ax.set_title(f"{div_col}", fontsize=9, fontweight="bold")
            continue

        sc_col, fit_col, sc_alpha = STRESS_COLOURS[label]
        ax.scatter(sub["do_station"], sub[div_col],
                   alpha=sc_alpha, s=12, color=sc_col, edgecolors="none")

        do_range = np.linspace(sub["do_station"].min(), sub["do_station"].max(), 100)
        fit_ok = False
        if HAS_GAM and len(sub) >= 10:
            try:
                gam = LinearGAM(s(0, n_splines=5)).fit(
                    sub["do_station"].values.reshape(-1,1), sub[div_col].values)
                pred = gam.predict(do_range.reshape(-1,1))
                ci   = gam.confidence_intervals(do_range.reshape(-1,1), width=0.95)
                ax.plot(do_range, pred, color=fit_col, lw=2, zorder=5)
                ax.fill_between(do_range, ci[:,0], ci[:,1], alpha=0.15, color=fit_col)
                fit_ok = True
            except Exception:
                pass
        if not fit_ok:
            sl, ic, lr, lp, _ = stats.linregress(sub["do_station"], sub[div_col])
            ax.plot(do_range, sl * do_range + ic, color=fit_col, lw=1.5, ls="--")

        ax.axvline(DO_HYPOXIC, color="grey", linestyle="--", lw=0.8, alpha=0.6)
        ax.axvline(DO_NORMOXIC, color="grey", linestyle=":", lw=0.8, alpha=0.5)

        r, p = stats.spearmanr(sub["do_station"], sub[div_col])
        sig = "***" if p<0.001 else ("**" if p<0.01 else ("*" if p<0.05 else "ns"))

        # Flag flat/uninformative all-station results explicitly
        interp = ""
        if row_i == 0 and abs(r) < 0.05:
            interp = "\n⚠ flat: spatial noise dominates"
        elif row_i == 0 and abs(r) < 0.12:
            interp = "\n⚠ weak: confounded"

        ax.set_title(f"{div_col}", fontsize=9, fontweight="bold")
        ax.set_xlabel("Bottom DO (mg/L)", fontsize=7)
        ax.set_ylabel(div_col, fontsize=7)
        info_col = "#c0392b" if (row_i==0 and abs(r)<0.12) else "black"
        ax.text(0.04, 0.96, f"r={r:+.2f} {sig}  n={len(sub)}{interp}",
                transform=ax.transAxes, fontsize=6.5, va="top",
                color=info_col,
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.85))

    # Row labels
axes[0][0].set_ylabel("Shannon H'\n(All stations)", fontsize=8)
axes[1][0].set_ylabel("Shannon H'\n(Stressed, DO≤4)", fontsize=8)

# Add row annotations
for row_i, (row_label, row_color, row_note) in enumerate([
    ("ALL STATIONS  ←  flat or confounded; dominated by spatial/historical noise",
     "#7f8c8d", 0.01),
    ("STRESSED (DO≤4)  ←  ecologically interpretable signal present",
     "#27ae60", 0.01),
]):
    fig.text(0.01, 0.95 - row_i*0.49, row_label,
             fontsize=8, color=row_color, style="italic",
             transform=fig.transFigure)

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig("figures/step3_gam_diversity_vs_do.png", dpi=150, bbox_inches="tight")
plt.close()
print("  → figures/step3_gam_diversity_vs_do.png")

# Fig 2 — Spearman heatmaps
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

for ax, (title, spear_df, n_recs) in zip(axes, [
    ("All stations", spear_all, len(sub_all)),
    (f"Stressed stations (DO≤4, n={len(sub_str)})", spear_str, len(sub_str))
]):
    pivot = spear_df.pivot(index="Diversity", columns="EnvVar", values="r")
    pivot = pivot.reindex(index=DIVERSITY_INDICES, columns=ENV_VARS)
    pivot.columns = [ENV_LABELS.get(c,c) for c in pivot.columns]
    p_pivot = spear_df.pivot(index="Diversity", columns="EnvVar", values="p")
    p_pivot = p_pivot.reindex(index=DIVERSITY_INDICES, columns=ENV_VARS)

    im = ax.imshow(pivot.values.astype(float), cmap="RdBu_r",
                   vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, rotation=30, ha="right", fontsize=9)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index, fontsize=9)
    ax.set_title(f"{title}\n(n={n_recs})", fontweight="bold")

    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            r_val = pivot.values[i,j]
            p_val = p_pivot.values[i,j]
            if np.isnan(r_val): continue
            sig = "***" if p_val<0.001 else ("**" if p_val<0.01 else ("*" if p_val<0.05 else ""))
            txt_col = "white" if abs(r_val) > 0.6 else "black"
            ax.text(j, i, f"{r_val:.2f}{sig}", ha="center", va="center",
                    fontsize=8, color=txt_col, fontweight="bold")
    plt.colorbar(im, ax=ax, label="Spearman r", shrink=0.8)

plt.tight_layout()
plt.savefig("figures/step3_spearman_heatmap.png", dpi=150, bbox_inches="tight")
plt.close()
print("  → figures/step3_spearman_heatmap.png")

# Fig 2b — Within-bay Spearman: diversity vs DO
if len(bay_spear_df) > 0:
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle(
        "Within-Bay Spearman r: Diversity vs Bottom DO\n"
        "SIS-wide analysis conflates bays with different hypoxia regimes — "
        "within-bay signal is stronger",
        fontweight="bold", fontsize=10)

    bays = ["Hiroshima Bay", "Osaka Bay", "Ise Bay", "SIS (other)"]
    bay_colors = ["#d73027", "#fc8d59", "#4575b4", "#74add1"]

    for ax, div_col in zip(axes, TARGET_DIVS):
        for subset_label, alpha, hatch in [("All", 0.65, ""), ("Stressed(DO≤4)", 0.9, "//")]:
            sub = bay_spear_df[(bay_spear_df["DiversityIndex"] == div_col) &
                                (bay_spear_df["Subset"] == subset_label)]
            x_pos = np.arange(len(bays))
            offset = -0.2 if subset_label == "All" else 0.2
            rs = []
            for bay in bays:
                row = sub[sub["Bay"] == bay]
                rs.append(row["Spearman_r"].values[0] if len(row) > 0 else np.nan)

            bars = ax.bar(x_pos + offset, rs, 0.38,
                          color=[bay_colors[i] for i in range(len(bays))],
                          alpha=alpha, hatch=hatch, edgecolor="k", lw=0.5,
                          label=subset_label)
            # Significance stars
            for i, (bay, r_val) in enumerate(zip(bays, rs)):
                row = sub[sub["Bay"] == bay]
                if len(row) == 0 or np.isnan(r_val):
                    continue
                sig = row["Significance"].values[0]
                n = row["n"].values[0]
                ypos = r_val + (0.02 if r_val >= 0 else -0.05)
                ax.text(x_pos[i] + offset, ypos, f"{sig}\nn={n}",
                        ha="center", fontsize=6.5, va="bottom" if r_val>=0 else "top")

        ax.axhline(0, color="k", lw=0.8)
        ax.axhline(0.30, color="green", lw=1, ls=":", alpha=0.7, label="r=0.30 (moderate)")
        ax.axhline(-0.30, color="green", lw=1, ls=":", alpha=0.7)
        ax.set_xticks(np.arange(len(bays)))
        ax.set_xticklabels([b.replace(" ", "\n") for b in bays], fontsize=9)
        ax.set_ylabel(f"Spearman r ({div_col} vs DO)", fontsize=10)
        ax.set_title(f"{div_col}", fontweight="bold", fontsize=11)
        ax.set_ylim(-0.7, 0.9)
        ax.yaxis.grid(True, alpha=0.3, ls="--")
        ax.set_axisbelow(True)
        ax.legend(fontsize=8)

    plt.tight_layout()
    plt.savefig("figures/step3_within_bay_spearman.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  → figures/step3_within_bay_spearman.png")

# Fig 3 — DO distribution at benthos stations
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
sub_all["do_station"].hist(bins=30, ax=axes[0], color="#4575b4", edgecolor="k", lw=0.3)
axes[0].axvline(DO_HYPOXIC, color="r", linestyle="--", lw=1.5, label="DO=2 (hypoxic)")
axes[0].axvline(DO_NORMOXIC, color="orange", linestyle=":", lw=1.5, label="DO=4 (normoxic)")
axes[0].set_xlabel("Station-level bottom DO (mg/L)")
axes[0].set_ylabel("Count")
axes[0].set_title("DO Distribution at Benthos Survey Stations", fontweight="bold")
axes[0].legend()

# Seasonal boxplots
sub_all.boxplot(column="do_station", by="Season", ax=axes[1],
                patch_artist=True,
                boxprops=dict(facecolor="#74add1", alpha=0.7))
axes[1].set_title("Station DO by Season", fontweight="bold")
axes[1].set_xlabel("Season")
axes[1].set_ylabel("Bottom DO (mg/L)")
axes[1].axhline(DO_HYPOXIC, color="r", linestyle="--", lw=1.5, label="DO=2 mg/L")
plt.suptitle("")
axes[1].legend()

plt.tight_layout()
plt.savefig("figures/step3_do_at_benthos_stations.png", dpi=150, bbox_inches="tight")
plt.close()
print("  → figures/step3_do_at_benthos_stations.png")

print("\n" + "=" * 60)
print("Step 3 COMPLETE")
print("=" * 60)
print(gam_df[["Subset","DiversityIndex","n","Spearman_r","Spearman_p","R2"]].to_string(index=False))
