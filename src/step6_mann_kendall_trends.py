"""
Step 6 — Mann-Kendall Trend Analysis
Long-term trends (1991–2024) in sediment quality and bottom DO by sea area.

Variables: TOC, Sulfides, ORP, COD, LOI, Clay%, Depth, DO
Groups: SIS (Seto Inland Sea), Tokyo Bay, Ise Bay + all combined

Outputs:
  data/processed/step6_mk_trends.csv
  figures/step6_*.png
"""

import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import warnings
warnings.filterwarnings("ignore")

os.makedirs("figures", exist_ok=True)

# ─────────────────────────────────────────────
# Try pymannkendall; fall back to scipy
# ─────────────────────────────────────────────
try:
    import pymannkendall as mk
    def mann_kendall(series):
        res = mk.original_test(series)
        return res.tau, res.p, res.slope, res.intercept, res.trend
    HAS_MK = True
    print("pymannkendall available")
except ImportError:
    HAS_MK = False
    print("pymannkendall not installed — using scipy.stats.kendalltau fallback")
    def mann_kendall(series):
        n    = len(series)
        x    = np.arange(n)
        tau, p = stats.kendalltau(x, series)
        # Sen's slope (simplified)
        slopes = []
        for i in range(n):
            for j in range(i+1, n):
                if (j - i) > 0:
                    slopes.append((series.iloc[j] - series.iloc[i]) / (j - i))
        slope = float(np.median(slopes)) if slopes else np.nan
        intercept = float(np.median(series.values) - slope * np.median(x))
        trend = "increasing" if (p < 0.05 and tau > 0) else ("decreasing" if (p < 0.05 and tau < 0) else "no trend")
        return tau, p, slope, intercept, trend

# ─────────────────────────────────────────────
# Load data
# ─────────────────────────────────────────────
print("=" * 60)
print("Loading data")
print("=" * 60)

master = pd.read_csv("data/processed/master_sediment_env.csv", encoding="utf-8-sig")
rename_map = {"硫化物": "Sulfides", "強熱減量": "LOI", "粘土分": "Clay_pct", "水深": "Depth_m"}
master.rename(columns=rename_map, inplace=True)

master["Year"] = pd.to_numeric(master.get("Year", master.get("年", np.nan)), errors="coerce")
master["Month"] = pd.to_numeric(master.get("Month", master.get("月", np.nan)), errors="coerce")

# Define region labels
if "study_region" in master.columns:
    master["region_label"] = master["study_region"]
elif "sea_area" in master.columns:
    master["region_label"] = master["sea_area"].apply(
        lambda x: "Tokyo" if x == 100 else ("Ise" if x in [201, 202] else "SIS")
    )

print(f"Total records: {len(master)}")
print(f"Year range: {master['Year'].min():.0f}–{master['Year'].max():.0f}")
print(f"Regions: {master['region_label'].value_counts().to_dict()}")

# ─────────────────────────────────────────────
# Annual summer means by region
# ─────────────────────────────────────────────
SUMMER_VARS = ["TOC", "Sulfides", "ORP", "COD", "LOI", "Clay_pct", "Depth_m", "do_nearest"]
SUMMER_VARS = [c for c in SUMMER_VARS if c in master.columns]

summer = master[master["Season"] == "Summer"]
annual = (summer.groupby(["region_label", "Year"])[SUMMER_VARS]
          .mean().reset_index())

# Also compute all-SIS combined
all_sis = summer[summer["region_label"] == "SIS"]
sis_annual = all_sis.groupby("Year")[SUMMER_VARS].mean().reset_index()
sis_annual["region_label"] = "SIS"

# All regions combined
all_annual = summer.groupby("Year")[SUMMER_VARS].mean().reset_index()
all_annual["region_label"] = "All"

trend_df = pd.concat([annual, all_annual], ignore_index=True)

# ─────────────────────────────────────────────
# Mann-Kendall tests
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("Mann-Kendall trend tests (summer annual means)")
print("=" * 60)

results = []
for region in trend_df["region_label"].unique():
    sub = trend_df[trend_df["region_label"] == region].sort_values("Year")
    for var in SUMMER_VARS:
        s = sub[["Year", var]].dropna()
        if len(s) < 5:
            continue
        tau, p, slope, intercept, trend = mann_kendall(s[var])
        sig = "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else "ns"))
        trend_dir = "↑" if trend == "increasing" else ("↓" if trend == "decreasing" else "—")
        print(f"  {region:8s}  {var:12s}  tau={tau:+.3f}  p={p:.4f}  {sig}  {trend_dir}  slope={slope:+.4f}/yr")
        results.append({
            "Region": region, "Variable": var, "n_years": len(s),
            "Kendall_tau": round(tau, 4), "p_value": round(p, 4),
            "Sen_slope": round(slope, 6), "Intercept": round(intercept, 4),
            "Trend": trend, "Significance": sig
        })

results_df = pd.DataFrame(results)
results_df.to_csv("data/processed/step6_mk_trends.csv", index=False)
print(f"\nSaved {len(results_df)} trend tests to data/processed/step6_mk_trends.csv")

# ─────────────────────────────────────────────
# FIGURES
# ─────────────────────────────────────────────
print("\nGenerating figures …")

VAR_LABELS = {
    "TOC":       ("TOC (mg/g)",          "#e41a1c"),
    "Sulfides":  ("Sulfides (mg/g)",     "#984ea3"),
    "ORP":       ("ORP (mV)",            "#ff7f00"),
    "COD":       ("COD (mg/g)",          "#4daf4a"),
    "LOI":       ("LOI % (organic)",     "#377eb8"),
    "Clay_pct":  ("Clay %",              "#a65628"),
    "do_nearest":("Bottom DO (mg/L)",    "#f781bf"),
}

REGIONS = [r for r in ["All", "SIS", "Tokyo", "Ise"] if r in trend_df["region_label"].unique()]

# ── Fig 1: Multi-panel trend time series for SIS + All ──
plot_vars = [v for v in ["do_nearest", "TOC", "Sulfides", "ORP", "LOI"] if v in SUMMER_VARS]
n_vars = len(plot_vars)
fig, axes = plt.subplots(n_vars, 1, figsize=(12, 3 * n_vars), sharex=True)
if n_vars == 1:
    axes = [axes]
fig.suptitle("Annual Summer Means — Long-term Trends (1991–2024)\nMann-Kendall p<0.05: solid trend line",
             fontweight="bold", fontsize=12)

for ax, var in zip(axes, plot_vars):
    label, color = VAR_LABELS.get(var, (var, "#333333"))
    for region, ls, ms in zip(["All", "SIS"], ["-", "--"], ["o", "s"]):
        sub = trend_df[trend_df["region_label"] == region].sort_values("Year").dropna(subset=[var])
        if len(sub) < 3:
            continue
        ax.plot(sub["Year"], sub[var], ls, color=color, alpha=0.5 if region == "All" else 0.8,
                marker=ms, markersize=4, lw=1.2, label=f"{region}")
        # Draw Sen's slope line if significant
        # Recompute trend line using actual year values (intercept in results_df uses index-based x)
        res_row = results_df[(results_df["Region"] == region) & (results_df["Variable"] == var)]
        if len(res_row) > 0 and res_row.iloc[0]["p_value"] < 0.05:
            xr = sub["Year"].values.astype(float)
            yr = sub[var].values.astype(float)
            slope_fit, intercept_fit = np.polyfit(xr, yr, 1)
            ax.plot(xr, slope_fit * xr + intercept_fit, "-", color=color,
                    lw=2.5, alpha=0.9, zorder=5)
    ax.set_ylabel(label, fontsize=9)
    ax.yaxis.grid(True, alpha=0.3, linestyle=":")
    ax.set_axisbelow(True)
    # DO threshold reference lines
    if var == "do_nearest":
        ax.axhline(4.0, color="orange", lw=1, ls="--", alpha=0.7, label="Stress threshold")
        ax.axhline(2.0, color="red",    lw=1, ls="--", alpha=0.7, label="Hypoxia threshold")
    if ax == axes[0]:
        ax.legend(fontsize=8, loc="upper right")

axes[-1].set_xlabel("Year", fontsize=10)
plt.tight_layout()
plt.savefig("figures/step6_trend_timeseries.png", dpi=150, bbox_inches="tight")
plt.close()
print("  → figures/step6_trend_timeseries.png")

# ── Fig 2: Tau heatmap ──
pivot = results_df.pivot_table(index="Variable", columns="Region", values="Kendall_tau")
sig_pivot = results_df.pivot_table(index="Variable", columns="Region", values="p_value")

fig, ax = plt.subplots(figsize=(10, 6))
vars_plot  = [v for v in ["do_nearest","TOC","Sulfides","ORP","COD","LOI","Clay_pct"] if v in pivot.index]
regs_plot  = [r for r in ["All","SIS","Tokyo","Ise"] if r in pivot.columns]
data_plot  = pivot.loc[vars_plot, regs_plot].values

im = ax.imshow(data_plot, cmap="RdBu_r", vmin=-0.6, vmax=0.6, aspect="auto")
plt.colorbar(im, ax=ax, label="Kendall τ")

ax.set_xticks(range(len(regs_plot)))
ax.set_xticklabels(regs_plot, fontsize=11)
ax.set_yticks(range(len(vars_plot)))
ax.set_yticklabels([VAR_LABELS.get(v, (v,""))[0] for v in vars_plot], fontsize=10)
ax.set_title("Mann-Kendall Kendall τ by Variable and Region\n(* p<0.05, ** p<0.01, *** p<0.001)",
             fontweight="bold", fontsize=12)

for i, var in enumerate(vars_plot):
    for j, reg in enumerate(regs_plot):
        if var in sig_pivot.index and reg in sig_pivot.columns:
            p = sig_pivot.loc[var, reg]
            tau_val = pivot.loc[var, reg] if (var in pivot.index and reg in pivot.columns) else np.nan
            if np.isnan(p) or np.isnan(tau_val):
                label = "–"
            else:
                sig = "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else ""))
                label = f"{tau_val:+.2f}{sig}"
            ax.text(j, i, label, ha="center", va="center", fontsize=9,
                    color="white" if abs(tau_val if not np.isnan(tau_val) else 0) > 0.35 else "black")

plt.tight_layout()
plt.savefig("figures/step6_tau_heatmap.png", dpi=150, bbox_inches="tight")
plt.close()
print("  → figures/step6_tau_heatmap.png")

print("\n" + "=" * 60)
print("Step 6 COMPLETE")
print("=" * 60)

# Summary of significant trends
sig_trends = results_df[results_df["p_value"] < 0.05]
print(f"\nSignificant trends (p<0.05): {len(sig_trends)} of {len(results_df)}")
for _, row in sig_trends.iterrows():
    dir_sym = "↑" if row["Trend"] == "increasing" else "↓"
    print(f"  {row['Region']:8s}  {row['Variable']:12s}  {dir_sym}  τ={row['Kendall_tau']:+.3f}  p={row['p_value']:.4f}")
