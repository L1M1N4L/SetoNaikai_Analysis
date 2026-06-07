"""
Step 1 — Environmental Characterisation and Hypoxia Zone Identification
Reproduces the logic of Figures 2 and 3 of Lai et al. (2024).

Inputs:
  data/raw/Fixed_line_survey/fixed_line_survey_long_hiroshima.csv
  data/raw/Fixed_line_survey/fixed_line_survey_long_osaka.csv
  data/raw/Fixed_line_survey/fixed_station_observations_osaka.csv
  data/raw/Fixed_line_survey/station_meta.csv
  data/processed/env_bottom_timeseries.csv  (multi-decadal SIS-wide)

Outputs:
  data/processed/step1_hiroshima_bottom.csv
  data/processed/step1_osaka_bottom.csv
  data/processed/step1_spearman_hiroshima.csv
  data/processed/step1_spearman_osaka.csv
  data/processed/step1_hypoxia_summary.csv
  data/processed/step1_multidecadal_summer_bottom.csv
  figures/step1_*.png
"""

import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import warnings
warnings.filterwarnings("ignore")

os.makedirs("figures", exist_ok=True)
os.makedirs("data/processed", exist_ok=True)

# ─────────────────────────────────────────────
# Shared constants (from agent.md)
# ─────────────────────────────────────────────
SUMMER_MONTHS   = [6, 7, 8, 9]
DO_NORMOXIC     = 4.0
DO_HYPOXIC      = 2.0
DO_SEVERE       = 1.0
DO_NEAR_ANOXIC  = 0.5
STRAT_THRESHOLD = 3.0   # °C, strong thermocline

DO_COLOURS = {
    "Normoxic (>4)":        "#2166ac",
    "Mod. stress (2–4)":    "#fed976",
    "Hypoxic (≤2)":         "#f03b20",
    "Severely hypoxic (≤1)":"#67000d",
}

def classify_do(do):
    if pd.isna(do):
        return "Unknown"
    if do <= DO_SEVERE:
        return "Severely hypoxic (≤1)"
    if do <= DO_HYPOXIC:
        return "Hypoxic (≤2)"
    if do <= DO_NORMOXIC:
        return "Mod. stress (2–4)"
    return "Normoxic (>4)"

def spearman_table(df, response, predictors):
    rows = []
    for p in predictors:
        sub = df[[response, p]].dropna()
        if len(sub) < 5:
            rows.append({"Variable": p, "r": np.nan, "p": np.nan, "n": len(sub)})
            continue
        r, p_val = stats.spearmanr(sub[response], sub[p])
        rows.append({"Variable": p, "r": round(r, 3), "p": round(p_val, 4), "n": len(sub)})
    return pd.DataFrame(rows)

# ─────────────────────────────────────────────
# 1A. Hiroshima — parse, classify, stratify
# ─────────────────────────────────────────────
print("=" * 60)
print("1A. Hiroshima fixed-line survey (2014)")
print("=" * 60)

hiro_raw = pd.read_csv(
    "data/raw/Fixed_line_survey/fixed_line_survey_long_hiroshima.csv"
)
print(f"Raw: {hiro_raw.shape}  |  Depths: {hiro_raw['Depth'].unique()}")

# Parse depth — "Bottom" as a special flag, numeric otherwise
hiro_raw["depth_m"] = pd.to_numeric(
    hiro_raw["Depth"].replace("Bottom", np.nan), errors="coerce"
)
hiro_raw["is_bottom"] = hiro_raw["Depth"] == "Bottom"

# Surface layer = 0 m
surf = hiro_raw[hiro_raw["Depth"] == "0m"][["Month", "Station", "Temperature"]]\
         .rename(columns={"Temperature": "Temp_surface"})

# Bottom layer
bot  = hiro_raw[hiro_raw["is_bottom"]].copy()

# Merge surface temp onto bottom for stratification index
hiro_bot = bot.merge(surf, on=["Month", "Station"], how="left")
hiro_bot["Strat_index"] = hiro_bot["Temp_surface"] - hiro_bot["Temperature"]

# DO classification
hiro_bot["DO_class"]   = hiro_bot["DO"].apply(classify_do)
hiro_bot["is_summer"]  = hiro_bot["Month"].isin(SUMMER_MONTHS)
hiro_bot["is_hypoxic"] = hiro_bot["DO"] <= DO_HYPOXIC

print(f"Bottom-layer records: {len(hiro_bot)}")
print(f"\nDO regime counts (all months):")
print(hiro_bot["DO_class"].value_counts())
print(f"\nSummer hypoxic stations (DO≤2):")
summer_hyp = hiro_bot[hiro_bot["is_summer"] & hiro_bot["is_hypoxic"]]
print(summer_hyp[["Month", "Station", "DO", "Strat_index"]].to_string(index=False))

# Spearman correlations — bottom DO vs env vars
print(f"\nSpearman correlations (Hiroshima bottom DO):")
spear_hiro = spearman_table(
    hiro_bot, "DO",
    ["Temperature", "Salinity", "Strat_index"]
)
print(spear_hiro.to_string(index=False))

# Save
hiro_bot.to_csv("data/processed/step1_hiroshima_bottom.csv", index=False)
spear_hiro.to_csv("data/processed/step1_spearman_hiroshima.csv", index=False)

# ─────────────────────────────────────────────
# 1B. Station metadata — parse coordinates
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("1B. Station metadata — coordinate parsing")
print("=" * 60)

meta_raw = pd.read_csv("data/raw/Fixed_line_survey/station_meta.csv")
print(meta_raw.head())

def parse_dm(s):
    """Parse 'DD MM.mm' or 'DD MM' degree-minute string to decimal degrees."""
    s = str(s).strip()
    parts = s.split()
    if len(parts) == 2:
        return float(parts[0]) + float(parts[1]) / 60
    return float(s)

meta_raw["lat_dd"] = meta_raw["Latitude_N"].apply(parse_dm)
meta_raw["lon_dd"] = meta_raw["Longitude_E"].apply(parse_dm)
print(f"\nParsed coordinates:")
print(meta_raw[["Station_ID", "lat_dd", "lon_dd", "Nominal_Depth_m"]].to_string(index=False))

# ─────────────────────────────────────────────
# 1C. Osaka — stratification index (no DO)
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("1C. Osaka fixed-line survey (2016) — stratification index")
print("=" * 60)

osaka_raw = pd.read_csv(
    "data/raw/Fixed_line_survey/fixed_line_survey_long_osaka.csv"
)
print(f"Raw: {osaka_raw.shape}  |  Depths: {osaka_raw['Depth'].unique()}")

# Surface = 0m, bottom = "Bottom"
osa_surf = osaka_raw[osaka_raw["Depth"] == "0m"][["Month","Station","Temperature"]]\
              .rename(columns={"Temperature": "Temp_surface"})
osa_bot  = osaka_raw[osaka_raw["Depth"] == "Bottom"].copy()

osaka_bot = osa_bot.merge(osa_surf, on=["Month","Station"], how="left")
osaka_bot = osaka_bot.merge(
    meta_raw[["Station_ID","Nominal_Depth_m","lat_dd","lon_dd"]],
    left_on="Station", right_on="Station_ID", how="left"
)
osaka_bot["Strat_index"] = osaka_bot["Temp_surface"] - osaka_bot["Temperature"]
osaka_bot["strong_thermo"] = osaka_bot["Strat_index"] > STRAT_THRESHOLD
osaka_bot["is_summer"] = osaka_bot["Month"].isin(SUMMER_MONTHS)

print(f"Bottom records: {len(osaka_bot)}")
print(f"Strong thermocline (ΔT > 3°C): {osaka_bot['strong_thermo'].sum()} records "
      f"({osaka_bot['strong_thermo'].mean()*100:.1f}%)")
print(f"Summer strong thermocline: "
      f"{osaka_bot[osaka_bot['is_summer']]['strong_thermo'].sum()}")

# Spearman: stratification vs depth
print(f"\nSpearman correlations (Osaka stratification index):")
spear_osa = spearman_table(
    osaka_bot, "Strat_index",
    ["Temperature", "Salinity", "Nominal_Depth_m"]
)
print(spear_osa.to_string(index=False))

osaka_bot.to_csv("data/processed/step1_osaka_bottom.csv", index=False)
spear_osa.to_csv("data/processed/step1_spearman_osaka.csv", index=False)

# ─────────────────────────────────────────────
# 1D. Fixed-station meteorological forcing
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("1D. Osaka fixed-station meteorological context")
print("=" * 60)

meteo = pd.read_csv("data/raw/Fixed_line_survey/fixed_station_observations_osaka.csv")
meteo["Date"] = pd.to_datetime(meteo["Date"], errors="coerce")
meteo["is_summer"] = meteo["Month"].isin(SUMMER_MONTHS)

print(f"Records: {len(meteo)}  |  Months: {sorted(meteo['Month'].dropna().unique())}")
print(f"\nSummer vs non-summer wind speed (m/s):")
print(meteo.groupby("is_summer")["Wind_Speed_10min_Avg_m_s"].describe().round(2))
print(f"\nSummer vs non-summer rainfall (mm):")
print(meteo.groupby("is_summer")["Rainfall_mm"].describe().round(2))

# ─────────────────────────────────────────────
# 1E. Multi-decadal SIS-wide summer bottom DO
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("1E. Multi-decadal SIS summer bottom DO (env_bottom_timeseries)")
print("=" * 60)

env = pd.read_csv("data/processed/env_bottom_timeseries.csv", encoding="utf-8-sig")
env_sis_sum = env[
    (env["region"] == "SIS") &
    (env["surveymont"].isin(SUMMER_MONTHS))
].copy()

env_sis_sum["DO_class"]   = env_sis_sum["do_2"].apply(classify_do)
env_sis_sum["is_hypoxic"] = env_sis_sum["do_2"] <= DO_HYPOXIC

print(f"SIS summer bottom records: {len(env_sis_sum):,}")
print(f"Year range: {env_sis_sum['surveyyear'].min():.0f}–{env_sis_sum['surveyyear'].max():.0f}")
print(f"\nDO regime distribution:")
print(env_sis_sum["DO_class"].value_counts())
print(f"\nHypoxic prevalence by decade:")
env_sis_sum["decade"] = (env_sis_sum["surveyyear"] // 10 * 10).astype(int)
dec = env_sis_sum.groupby("decade").agg(
    n=("do_2","count"),
    hypoxic=("is_hypoxic","sum"),
    mean_do=("do_2","mean")
).assign(pct_hypoxic=lambda x: (x["hypoxic"]/x["n"]*100).round(1))
print(dec)

env_sis_sum.to_csv("data/processed/step1_multidecadal_summer_bottom.csv", index=False)

# ─────────────────────────────────────────────
# 1F. Hypoxia summary table
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("1F. Hypoxia prevalence summary")
print("=" * 60)

summary = {
    "Hiroshima 2014 (all months)": {
        "n_stations":  hiro_bot["Station"].nunique(),
        "n_records":   len(hiro_bot),
        "n_hypoxic":   (hiro_bot["DO"] <= DO_HYPOXIC).sum(),
        "pct_hypoxic": round((hiro_bot["DO"] <= DO_HYPOXIC).mean()*100, 1),
        "mean_DO":     round(hiro_bot["DO"].mean(), 2),
        "min_DO":      round(hiro_bot["DO"].min(), 2),
    },
    "Hiroshima 2014 (summer only)": {
        "n_stations":  hiro_bot[hiro_bot["is_summer"]]["Station"].nunique(),
        "n_records":   hiro_bot["is_summer"].sum(),
        "n_hypoxic":   (hiro_bot["is_summer"] & (hiro_bot["DO"]<=DO_HYPOXIC)).sum(),
        "pct_hypoxic": round(
            (hiro_bot[hiro_bot["is_summer"]]["DO"]<=DO_HYPOXIC).mean()*100, 1),
        "mean_DO":     round(hiro_bot[hiro_bot["is_summer"]]["DO"].mean(), 2),
        "min_DO":      round(hiro_bot[hiro_bot["is_summer"]]["DO"].min(), 2),
    },
    "SIS-wide 1981-2024 (summer bottom)": {
        "n_stations":  env_sis_sum["zettaicode"].nunique(),
        "n_records":   len(env_sis_sum),
        "n_hypoxic":   env_sis_sum["is_hypoxic"].sum(),
        "pct_hypoxic": round(env_sis_sum["is_hypoxic"].mean()*100, 1),
        "mean_DO":     round(env_sis_sum["do_2"].mean(), 2),
        "min_DO":      round(env_sis_sum["do_2"].min(), 2),
    },
}
sum_df = pd.DataFrame(summary).T
print(sum_df.to_string())
sum_df.to_csv("data/processed/step1_hypoxia_summary.csv")

# ─────────────────────────────────────────────
# FIGURES
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("Generating figures …")
print("=" * 60)

# Fig 1a — Hiroshima bottom DO by station and month (heatmap)
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

pivot_do = hiro_bot.pivot_table(
    index="Station", columns="Month", values="DO", aggfunc="mean"
)
im = axes[0].imshow(
    pivot_do.values, aspect="auto", cmap="RdYlBu",
    vmin=0, vmax=10
)
axes[0].set_xticks(range(len(pivot_do.columns)))
axes[0].set_xticklabels(pivot_do.columns, fontsize=9)
axes[0].set_yticks(range(len(pivot_do.index)))
axes[0].set_yticklabels(pivot_do.index, fontsize=8)
axes[0].set_xlabel("Month")
axes[0].set_ylabel("Station")
axes[0].set_title("Hiroshima Bay — Bottom DO (mg/L) by Station × Month (2014)",
                  fontweight="bold")
plt.colorbar(im, ax=axes[0], label="DO (mg/L)")

# Add hypoxia threshold line annotation
for j, month in enumerate(pivot_do.columns):
    for i, station in enumerate(pivot_do.index):
        val = pivot_do.loc[station, month]
        if not np.isnan(val) and val <= DO_HYPOXIC:
            axes[0].add_patch(
                mpatches.Rectangle((j-0.5, i-0.5), 1, 1,
                                   fill=False, edgecolor="black", lw=2)
            )

# Fig 1b — Stratification index vs month (Osaka)
pivot_strat = osaka_bot.pivot_table(
    index="Station", columns="Month", values="Strat_index", aggfunc="mean"
)
im2 = axes[1].imshow(
    pivot_strat.values, aspect="auto", cmap="YlOrRd",
    vmin=0, vmax=12
)
axes[1].set_xticks(range(len(pivot_strat.columns)))
axes[1].set_xticklabels(pivot_strat.columns, fontsize=9)
axes[1].set_yticks(range(len(pivot_strat.index)))
axes[1].set_yticklabels(pivot_strat.index, fontsize=8)
axes[1].set_xlabel("Month")
axes[1].set_ylabel("Station")
axes[1].set_title("Osaka Bay — Surface–Bottom ΔT (°C) Stratification Index (2016)",
                  fontweight="bold")
plt.colorbar(im2, ax=axes[1], label="ΔT surface−bottom (°C)")

# Mark strong thermocline (>3°C)
for j, month in enumerate(pivot_strat.columns):
    for i, station in enumerate(pivot_strat.index):
        val = pivot_strat.loc[station, month]
        if not np.isnan(val) and val > STRAT_THRESHOLD:
            axes[1].add_patch(
                mpatches.Rectangle((j-0.5, i-0.5), 1, 1,
                                   fill=False, edgecolor="black", lw=1.5)
            )

plt.tight_layout()
plt.savefig("figures/step1_do_and_stratification_heatmaps.png", dpi=150, bbox_inches="tight")
plt.close()
print("  → figures/step1_do_and_stratification_heatmaps.png")

# Fig 2 — Spearman correlation matrix (Hiroshima)
fig, ax = plt.subplots(figsize=(7, 4))
labels  = spear_hiro["Variable"].tolist()
r_vals  = spear_hiro["r"].tolist()
p_vals  = spear_hiro["p"].tolist()
colors  = ["#d73027" if r < 0 else "#4575b4" for r in r_vals]
bars    = ax.barh(labels, r_vals, color=colors, edgecolor="k", linewidth=0.5)
ax.axvline(0, color="k", linewidth=0.8)
for i, (r, p) in enumerate(zip(r_vals, p_vals)):
    sig = "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else "ns"))
    ax.text(r + (0.02 if r >= 0 else -0.02), i,
            f"r={r:.2f} {sig}", va="center",
            ha="left" if r >= 0 else "right", fontsize=9)
ax.set_xlabel("Spearman r")
ax.set_title("Spearman Correlations with Bottom DO\nHiroshima Bay 2014",
             fontweight="bold")
ax.set_xlim(-1, 1)
plt.tight_layout()
plt.savefig("figures/step1_spearman_hiroshima.png", dpi=150, bbox_inches="tight")
plt.close()
print("  → figures/step1_spearman_hiroshima.png")

# Fig 3 — Multi-decadal SIS summer DO distribution (violin/box per decade)
fig, axes = plt.subplots(1, 2, figsize=(16, 5))

# Violin by decade
decades = sorted(env_sis_sum["decade"].unique())
data_by_decade = [env_sis_sum[env_sis_sum["decade"] == d]["do_2"].dropna().values
                  for d in decades]
parts = axes[0].violinplot(data_by_decade, positions=range(len(decades)),
                            showmedians=True, showextrema=True)
for pc in parts["bodies"]:
    pc.set_facecolor("#4575b4")
    pc.set_alpha(0.6)
axes[0].axhline(DO_HYPOXIC, color="#f03b20", linestyle="--", lw=1.5,
                label=f"Hypoxic threshold ({DO_HYPOXIC} mg/L)")
axes[0].axhline(DO_NORMOXIC, color="#fd8d3c", linestyle=":", lw=1.5,
                label=f"Normoxic threshold ({DO_NORMOXIC} mg/L)")
axes[0].set_xticks(range(len(decades)))
axes[0].set_xticklabels([str(d) + "s" for d in decades], fontsize=9)
axes[0].set_ylabel("Bottom DO (mg/L)")
axes[0].set_title("SIS-wide Summer Bottom DO Distribution by Decade\n(1981–2024)",
                  fontweight="bold")
axes[0].legend(fontsize=8)

# Annual mean DO trend
annual = env_sis_sum.groupby("surveyyear")["do_2"].agg(["mean","std","count"]).reset_index()
annual.columns = ["year","mean_do","std_do","n"]
axes[1].fill_between(
    annual["year"],
    annual["mean_do"] - annual["std_do"],
    annual["mean_do"] + annual["std_do"],
    alpha=0.2, color="#4575b4", label="±1 SD"
)
axes[1].plot(annual["year"], annual["mean_do"], color="#2166ac", lw=2, label="Annual mean")
axes[1].axhline(DO_HYPOXIC, color="#f03b20", linestyle="--", lw=1.5,
                label=f"Hypoxic threshold")
axes[1].axhline(DO_NORMOXIC, color="#fd8d3c", linestyle=":", lw=1.5,
                label=f"Normoxic threshold")
# Add linear trend
slope, intercept, r, p, _ = stats.linregress(annual["year"], annual["mean_do"])
trend_y = slope * annual["year"] + intercept
axes[1].plot(annual["year"], trend_y, "k--", lw=1,
             label=f"Trend: {slope*10:+.3f} mg/L/decade (p={p:.3f})")
axes[1].set_xlabel("Year")
axes[1].set_ylabel("Mean Summer Bottom DO (mg/L)")
axes[1].set_title("Annual Mean Summer Bottom DO — SIS 1981–2024", fontweight="bold")
axes[1].legend(fontsize=8)

plt.tight_layout()
plt.savefig("figures/step1_multidecadal_do_trend.png", dpi=150, bbox_inches="tight")
plt.close()
print("  → figures/step1_multidecadal_do_trend.png")

# Fig 4 — DO regime pie charts: summer vs all
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
for ax, (label, subset) in zip(axes, [
    ("Summer", hiro_bot[hiro_bot["is_summer"]]),
    ("All months", hiro_bot)
]):
    counts = subset["DO_class"].value_counts()
    ordered = [k for k in DO_COLOURS if k in counts.index]
    vals    = [counts[k] for k in ordered]
    cols    = [DO_COLOURS[k] for k in ordered]
    wedges, texts, autotexts = ax.pie(
        vals, labels=ordered, colors=cols,
        autopct="%1.1f%%", startangle=140,
        textprops={"fontsize": 9}
    )
    ax.set_title(f"Hiroshima Bay DO Regimes\n{label} (2014)", fontweight="bold")

plt.tight_layout()
plt.savefig("figures/step1_do_regime_pies.png", dpi=150, bbox_inches="tight")
plt.close()
print("  → figures/step1_do_regime_pies.png")

# Fig 5 — Meteorological forcing: wind and rainfall seasonality
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6), sharex=True)

meteo_monthly = meteo.groupby("Month").agg(
    wind_mean=("Wind_Speed_10min_Avg_m_s", "mean"),
    wind_sd=("Wind_Speed_10min_Avg_m_s", "std"),
    rain_mean=("Rainfall_mm", "mean"),
    rain_sd=("Rainfall_mm", "std"),
).reset_index()

ax1.bar(meteo_monthly["Month"], meteo_monthly["wind_mean"],
        color="#4575b4", alpha=0.8, edgecolor="k", lw=0.5)
ax1.fill_between(meteo_monthly["Month"],
                 meteo_monthly["wind_mean"] - meteo_monthly["wind_sd"],
                 meteo_monthly["wind_mean"] + meteo_monthly["wind_sd"],
                 alpha=0.3, color="#4575b4")
for m in SUMMER_MONTHS:
    ax1.axvspan(m-0.5, m+0.5, alpha=0.1, color="#f03b20")
ax1.set_ylabel("Avg wind speed (m/s)")
ax1.set_title("Osaka Bay Meteorological Forcing — Monthly Averages (2016)",
              fontweight="bold")

ax2.bar(meteo_monthly["Month"], meteo_monthly["rain_mean"],
        color="#74add1", alpha=0.8, edgecolor="k", lw=0.5)
for m in SUMMER_MONTHS:
    ax2.axvspan(m-0.5, m+0.5, alpha=0.1, color="#f03b20",
                label="Summer (Jun–Sep)" if m == SUMMER_MONTHS[0] else "")
ax2.set_ylabel("Rainfall (mm)")
ax2.set_xlabel("Month")
ax2.legend(fontsize=8)

plt.tight_layout()
plt.savefig("figures/step1_meteorological_forcing.png", dpi=150, bbox_inches="tight")
plt.close()
print("  → figures/step1_meteorological_forcing.png")

print("\n" + "=" * 60)
print("Step 1 COMPLETE")
print("=" * 60)
print(f"\nKey results:")
print(f"  Hiroshima 2014: {(hiro_bot['DO'] <= DO_HYPOXIC).sum()} hypoxic station-months "
      f"({(hiro_bot['DO'] <= DO_HYPOXIC).mean()*100:.1f}%)")
print(f"  Hiroshima summer: {(hiro_bot[hiro_bot['is_summer']]['DO'] <= DO_HYPOXIC).sum()} "
      f"hypoxic of {hiro_bot['is_summer'].sum()} records")
print(f"  SIS-wide summer: {env_sis_sum['is_hypoxic'].sum():,} hypoxic of "
      f"{len(env_sis_sum):,} records ({env_sis_sum['is_hypoxic'].mean()*100:.1f}%)")
print(f"  Osaka strong thermocline (ΔT>3°C): "
      f"{osaka_bot['strong_thermo'].sum()} of {len(osaka_bot)} records "
      f"({osaka_bot['strong_thermo'].mean()*100:.1f}%)")
print(f"\nOutputs: data/processed/step1_*.csv | figures/step1_*.png")
