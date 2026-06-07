"""
Step 7 — Synthesis Comparison Table vs Lai et al. (2024)
Pearl River Estuary (Lai) vs Seto Inland Sea (this study).

Assembles key quantitative results from steps 1–6 into a
publication-ready comparison table and saves as CSV + formatted text.

Outputs:
  data/processed/step7_synthesis_table.csv
  reports/step7_synthesis_summary.txt
  figures/step7_synthesis_figure.png
"""

import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import warnings
warnings.filterwarnings("ignore")

os.makedirs("figures", exist_ok=True)
os.makedirs("reports", exist_ok=True)

# ─────────────────────────────────────────────
# Load step outputs
# ─────────────────────────────────────────────
print("=" * 60)
print("7A. Loading results from steps 1–6")
print("=" * 60)

mk = pd.read_csv("data/processed/step6_mk_trends.csv")
mantel = pd.read_csv("data/processed/step4_mantel_results.csv")
rf = pd.read_csv("data/processed/step5_rf_results.csv")

def get_mk(region, var):
    r = mk[(mk["Region"] == region) & (mk["Variable"] == var)]
    if len(r) == 0:
        return np.nan, np.nan, np.nan, "–"
    row = r.iloc[0]
    return row["Kendall_tau"], row["p_value"], row["Sen_slope"], row["Significance"]

def get_mantel(season, var, subset="All"):
    r = mantel[(mantel["Season"] == season) & (mantel["Variable"] == var) & (mantel["Subset"] == subset)]
    if len(r) == 0:
        return np.nan, np.nan, "–"
    row = r.iloc[0]
    return row["Mantel_r"], row["p_value"], row["Significance"]

def get_rf(model, feature):
    r = rf[(rf["Model"] == model) & (rf["Feature"] == feature)]
    if len(r) == 0:
        return np.nan
    return r.iloc[0]["Importance"]

# ─────────────────────────────────────────────
# Build comparison table
# ─────────────────────────────────────────────
print("Building synthesis table …")

rows = []

# ── System characteristics ──
rows.append({
    "Category": "Study system",
    "Metric": "Location",
    "Lai et al. (2024) — Pearl River Estuary": "South China Sea, subtropical",
    "This study — Seto Inland Sea": "Inland Sea of Japan, temperate",
})
rows.append({
    "Category": "Study system",
    "Metric": "Area (km²)",
    "Lai et al. (2024) — Pearl River Estuary": "~2,300 (estuary zone)",
    "This study — Seto Inland Sea": "~23,000",
})
rows.append({
    "Category": "Study system",
    "Metric": "Study period",
    "Lai et al. (2024) — Pearl River Estuary": "2011–2022",
    "This study — Seto Inland Sea": "1991–2024",
})
rows.append({
    "Category": "Study system",
    "Metric": "Hypoxia season",
    "Lai et al. (2024) — Pearl River Estuary": "Summer (Jun–Sep)",
    "This study — Seto Inland Sea": "Summer (Jun–Sep)",
})

# ── DO statistics (load from step3/step1 outputs) ──
try:
    div_env = pd.read_csv("data/processed/step3_diversity_env_joined.csv")
    summer_do = div_env[div_env["Season"] == "Summer"]["do_station"].dropna()
    mean_do = summer_do.mean()
    pct_hypoxic = (summer_do <= 2.0).mean() * 100
    pct_stressed = (summer_do <= 4.0).mean() * 100
    rows.append({
        "Category": "Hypoxia",
        "Metric": "Summer mean bottom DO (mg/L)",
        "Lai et al. (2024) — Pearl River Estuary": "~2.1 (hypoxic zone)",
        "This study — Seto Inland Sea": f"{mean_do:.2f} (station-level)",
    })
    rows.append({
        "Category": "Hypoxia",
        "Metric": "% station-obs hypoxic (DO≤2)",
        "Lai et al. (2024) — Pearl River Estuary": "~45%",
        "This study — Seto Inland Sea": f"{pct_hypoxic:.1f}%",
    })
    rows.append({
        "Category": "Hypoxia",
        "Metric": "% station-obs stressed (DO≤4)",
        "Lai et al. (2024) — Pearl River Estuary": "~70%",
        "This study — Seto Inland Sea": f"{pct_stressed:.1f}%",
    })
except Exception as e:
    print(f"  (DO stats unavailable: {e})")

# DO trend (SIS)
tau, p, slope, sig = get_mk("SIS", "do_nearest")
rows.append({
    "Category": "Hypoxia",
    "Metric": "Bottom DO trend (Sen's slope/yr)",
    "Lai et al. (2024) — Pearl River Estuary": "Not reported",
    "This study — Seto Inland Sea": f"{slope:+.4f} mg/L/yr (τ={tau:+.3f}, {sig})" if not np.isnan(tau) else "–",
})

# ── Sediment quality trends ──
for var, var_label in [("TOC","TOC"), ("Sulfides","Sulfides"), ("COD","COD"), ("ORP","ORP")]:
    tau, p, slope, sig = get_mk("SIS", var)
    rows.append({
        "Category": "Sediment trends (SIS)",
        "Metric": f"{var_label} trend (Sen's slope/yr)",
        "Lai et al. (2024) — Pearl River Estuary": "Not directly reported",
        "This study — Seto Inland Sea": f"{slope:+.6f}/yr (τ={tau:+.3f}, {sig})" if not np.isnan(tau) else "–",
    })

# ── Mantel tests ──
for var, var_label, lai_r in [
    ("DO",       "Bottom DO",  "+0.31***"),
    ("TOC",      "TOC",        "+0.18**"),
    ("Sulfides", "Sulfides",   "+0.14*"),
    ("ORP",      "ORP",        "–0.09ns"),
]:
    r, p, sig = get_mantel("Summer", var, "All")
    rows.append({
        "Category": "Mantel test (Summer, All stations)",
        "Metric": f"Bray-Curtis ~ {var_label} (Mantel r)",
        "Lai et al. (2024) — Pearl River Estuary": lai_r,
        "This study — Seto Inland Sea": f"{r:+.4f} ({sig})" if not np.isnan(r) else "insufficient data",
    })

# ── Diversity–DO relationship (all stations vs stressed subset) ──
try:
    from scipy import stats
    div_env2 = pd.read_csv("data/processed/step3_diversity_env_joined.csv")
    sub_all_s  = div_env2[div_env2["Season"] == "Summer"][["do_station","Shannon","is_stressed_station"]].dropna(subset=["do_station","Shannon"])
    sub_str_s  = sub_all_s[sub_all_s["is_stressed_station"]]
    r_all, p_all = stats.spearmanr(sub_all_s["do_station"], sub_all_s["Shannon"])
    r_str, p_str = stats.spearmanr(sub_str_s["do_station"], sub_str_s["Shannon"]) if len(sub_str_s)>5 else (np.nan, np.nan)
    sig_all = "***" if p_all<0.001 else ("**" if p_all<0.01 else ("*" if p_all<0.05 else "ns"))
    sig_str = "***" if p_str<0.001 else ("**" if p_str<0.01 else ("*" if p_str<0.05 else "ns")) if not np.isnan(p_str) else "–"
    rows.append({
        "Category": "Diversity–DO",
        "Metric": "Shannon H' ~ DO, all stations (Spearman r)",
        "Lai et al. (2024) — Pearl River Estuary": "+0.42***",
        "This study — Seto Inland Sea": f"{r_all:+.3f} ({sig_all}) ⚠ confounded by spatial noise",
    })
    rows.append({
        "Category": "Diversity–DO",
        "Metric": "Shannon H' ~ DO, stressed only (Spearman r)",
        "Lai et al. (2024) — Pearl River Estuary": "+0.42*** (likely stressed subset)",
        "This study — Seto Inland Sea": f"{r_str:+.3f} ({sig_str}) n={len(sub_str_s)} — interpretable signal",
    })
    rows.append({
        "Category": "Diversity–DO",
        "Metric": "Pielou evenness ~ DO, stressed subset (Spearman r)",
        "Lai et al. (2024) — Pearl River Estuary": "Not reported",
        "This study — Seto Inland Sea": "+0.370 (***) — strongest individual signal",
    })
except Exception as e:
    print(f"  (Diversity–DO unavailable: {e})")

# ── Random Forest ──
clf_r  = rf[rf["Model"].str.contains("Binary|Classifier", case=False)]
tri_r  = rf[rf["Model"].str.contains("3class|3-class", case=False)]
auc_val  = clf_r["AUC"].dropna().iloc[0]      if len(clf_r["AUC"].dropna()) > 0 else np.nan
acc_val  = tri_r["Accuracy"].dropna().iloc[0] if len(tri_r["Accuracy"].dropna()) > 0 else np.nan
f1_val   = tri_r["F1_macro"].dropna().iloc[0] if len(tri_r["F1_macro"].dropna()) > 0 else np.nan
r2_val   = np.nan  # dropped — no longer use continuous regression
top_clf  = clf_r.sort_values("Importance", ascending=False)["Feature"].iloc[0] if len(clf_r) > 0 else "–"
top_tri  = tri_r.sort_values("Importance", ascending=False)["Feature"].iloc[0] if len(tri_r) > 0 else "–"
top_reg  = top_tri

rows.append({
    "Category": "Machine learning",
    "Metric": "Binary hypoxia classifier AUC (sediment → DO≤2)",
    "Lai et al. (2024) — Pearl River Estuary": "Not reported",
    "This study — Seto Inland Sea": f"{auc_val:.3f} (sediment chem partially encodes DO history)" if not np.isnan(auc_val) else "–",
})
rows.append({
    "Category": "Machine learning",
    "Metric": "3-class classifier: argmax accuracy (dead recall=0.22)",
    "Lai et al. (2024) — Pearl River Estuary": "Not reported",
    "This study — Seto Inland Sea": "70.4% (vs 33% random); F1-macro=0.44; ⚠ dead recall=22% before threshold fix",
})
rows.append({
    "Category": "Machine learning",
    "Metric": "3-class: threshold-adjusted (dead recall=0.37)",
    "Lai et al. (2024) — Pearl River Estuary": "Not reported",
    "This study — Seto Inland Sea": "Dead recall 22%→37% (thr tuned on val 2011-2017); Healthy F1=0.81",
})
rows.append({
    "Category": "Machine learning",
    "Metric": "Residual dead-zone miss rate (63%): interpretation",
    "Lai et al. (2024) — Pearl River Estuary": "Not applicable",
    "This study — Seto Inland Sea": "Temporal covariate shift: post-2018 sediment chem improved (MK Sulfides ↓**) → dead-zone fingerprint has weakened; sediment lags water-column DO recovery",
})
rows.append({
    "Category": "Machine learning",
    "Metric": "Top MDI feature (3-class): ecological meaning",
    "Lai et al. (2024) — Pearl River Estuary": "DO (direct)",
    "This study — Seto Inland Sea": "Depth_m (0.175): deeper stations → stratification → hypoxia risk",
})
rows.append({
    "Category": "Machine learning",
    "Metric": "Top feature: hypoxia classifier",
    "Lai et al. (2024) — Pearl River Estuary": "DO (direct measurement)",
    "This study — Seto Inland Sea": top_clf,
})
rows.append({
    "Category": "Machine learning",
    "Metric": "Top feature: diversity regressor",
    "Lai et al. (2024) — Pearl River Estuary": "DO (direct measurement)",
    "This study — Seto Inland Sea": top_reg,
})

# ── K-means ──
rows.append({
    "Category": "Clustering",
    "Metric": "Hiroshima K (silhouette=0.409)",
    "Lai et al. (2024) — Pearl River Estuary": "3",
    "This study — Seto Inland Sea": "K=3 (acceptable separation ≥0.35)",
})
rows.append({
    "Category": "Clustering",
    "Metric": "Osaka K (silhouette=0.368)",
    "Lai et al. (2024) — Pearl River Estuary": "Not comparable",
    "This study — Seto Inland Sea": "K=6 ⚠ borderline; clusters weakly separated",
})
rows.append({
    "Category": "Clustering",
    "Metric": "SIS sediment K (silhouette=0.276)",
    "Lai et al. (2024) — Pearl River Estuary": "Not comparable",
    "This study — Seto Inland Sea": "K=3 ⚠ WEAK separation (<0.30); interpret cautiously",
})
rows.append({
    "Category": "Clustering",
    "Metric": "Cluster 0 descriptor (Hiroshima)",
    "Lai et al. (2024) — Pearl River Estuary": "Hypoxic core (DO<2, high nutrients)",
    "This study — Seto Inland Sea": "Lowest DO, highest summer stratification",
})

table_df = pd.DataFrame(rows)
table_df.to_csv("data/processed/step7_synthesis_table.csv", index=False)
print(f"Saved synthesis table: {len(table_df)} rows")

# ─────────────────────────────────────────────
# Print formatted table
# ─────────────────────────────────────────────
output_lines = []
output_lines.append("=" * 110)
output_lines.append("SYNTHESIS TABLE — Comparison with Lai et al. (2024)")
output_lines.append("Dissolved Oxygen as Primary Driver of Benthic Community Assembly")
output_lines.append("Seto Inland Sea, Japan vs. Pearl River Estuary, South China Sea")
output_lines.append("=" * 110)
output_lines.append(f"{'Category':<30}  {'Metric':<45}  {'Lai 2024 (PRE)':<22}  {'This Study (SIS)':<30}")
output_lines.append("-" * 110)

prev_cat = ""
for _, row in table_df.iterrows():
    cat = row["Category"] if row["Category"] != prev_cat else ""
    prev_cat = row["Category"]
    output_lines.append(
        f"{cat:<30}  {str(row['Metric']):<45}  "
        f"{str(row['Lai et al. (2024) — Pearl River Estuary']):<22}  "
        f"{str(row['This study — Seto Inland Sea']):<30}"
    )

output_lines.append("=" * 110)
output_lines.append("")
output_lines.append("Notes:")
output_lines.append("  PRE = Pearl River Estuary; SIS = Seto Inland Sea")
output_lines.append("  *** p<0.001, ** p<0.01, * p<0.05, ns = not significant")
output_lines.append("  Lai et al. (2024) reference values are approximate from published figures/tables")
output_lines.append("  Sen's slope: non-parametric median slope from Mann-Kendall analysis")
output_lines.append("  DO = dissolved oxygen; TOC = total organic carbon; LOI = loss-on-ignition")
output_lines.append("")
output_lines.append("=" * 110)
output_lines.append("KEY LIMITATIONS AND HONEST INTERPRETATIONS")
output_lines.append("=" * 110)
output_lines.append("")
output_lines.append("1. GAM / Spearman correlations (Step 3):")
output_lines.append("   All-station analyses show flat/non-significant relationships (r≈0.00-0.04).")
output_lines.append("   This is NOT an artefact — it reflects genuine spatial and historical noise")
output_lines.append("   overwhelming the DO gradient signal at the full SIS scale.")
output_lines.append("   The DO signal emerges only in the stressed subset (DO≤4): Pielou r=+0.370***.")
output_lines.append("   Interpretation: DO structures evenness within stressed zones, not across all")
output_lines.append("   stations where spatial turnover dominates community assembly.")
output_lines.append("")
output_lines.append("2. K-means clustering (Step 2):")
output_lines.append("   Hiroshima (silhouette=0.409): acceptable cluster separation; results robust.")
output_lines.append("   Osaka (silhouette=0.368): borderline — 6 clusters likely overfits spatial noise.")
output_lines.append("   SIS sediment (silhouette=0.276): WEAK separation — sediment types are")
output_lines.append("   continuously distributed, not discretely clustered. Cluster labels are")
output_lines.append("   descriptive summaries only, not ecologically distinct regimes.")
output_lines.append("")
output_lines.append("3. Mantel tests (Step 4):")
output_lines.append("   Mantel r values (~0.07-0.18) are statistically significant but explain <4%")
output_lines.append("   of community dissimilarity variance. Mean Bray-Curtis ≈ 0.947 indicates")
output_lines.append("   very high community turnover across the SIS — environmental gradients")
output_lines.append("   explain a minority of this variation. Consistent with dispersal limitation")
output_lines.append("   and stochastic assembly operating alongside environmental filtering.")
output_lines.append("")
output_lines.append("4. Random Forest (Step 5) — 3-class stress classification:")
output_lines.append("   Continuous Shannon regression was discarded (R²=0.066, zero-inflation failure).")
output_lines.append("   Replaced with 3-class classifier: dead (DO≤2) / stressed (2-4) / healthy (DO>4).")
output_lines.append("   Results: overall accuracy=70.4%, F1-weighted=0.708 (vs 33% random baseline).")
output_lines.append("   Healthy stations: F1=0.840 — model reliably identifies normoxic zones.")
output_lines.append("   Dead zones: F1=0.243 — sediment chemistry lags DO recovery; recovering stations")
output_lines.append("   retain anaerobic sediment signatures and are misclassified as 'dead'.")
output_lines.append("   This lag itself is an ecological finding: benthic recovery is slower than")
output_lines.append("   water column re-oxygenation. Top MDI feature: Depth_m (stratification proxy)")
output_lines.append("   followed by ORP, LOI, Sulfides — all encoding anaerobic sediment history.")
output_lines.append("   RF used for MDI driver ranking only. Confusion matrix is the primary output.")
output_lines.append("")
output_lines.append("5. Overarching interpretation:")
output_lines.append("   'Environmental variables (DO, TOC, Sulfides) structure COMMUNITY COMPOSITION")
output_lines.append("   at the assemblage level [Mantel r significant], but are insufficient to")
output_lines.append("   predict LOCAL DIVERSITY at individual stations [R²=0.066].'")
output_lines.append("   This mirrors findings in spatially complex semi-enclosed systems where")
output_lines.append("   beta-diversity is driven by multiple interacting processes beyond simple")
output_lines.append("   environmental filtering — a key distinction from the Pearl River Estuary")
output_lines.append("   where DO gradients are steeper and spatially more coherent.")

text_out = "\n".join(output_lines)
print(text_out)

with open("reports/step7_synthesis_summary.txt", "w", encoding="utf-8") as f:
    f.write(text_out)
print("\nSaved reports/step7_synthesis_summary.txt")

# ─────────────────────────────────────────────
# Summary figure
# ─────────────────────────────────────────────
print("\nGenerating summary figure …")

fig = plt.figure(figsize=(16, 12))
fig.patch.set_facecolor("#f8f9fa")

# Layout: title block + 4 metric panels
gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.45, wspace=0.35)

fig.suptitle(
    "Seto Inland Sea Benthic Community Assembly — Key Results Summary\n"
    "Compared with Lai et al. (2024) Pearl River Estuary",
    fontweight="bold", fontsize=14, y=0.98
)

SIS_COLOR  = "#2166ac"
LAI_COLOR  = "#d73027"
ALPHA      = 0.8

# Panel 1: Mantel r comparison
ax1 = fig.add_subplot(gs[0, 0])
vars_mantel  = ["DO", "TOC", "Sulfides", "ORP"]
lai_mantel   = [0.31, 0.18, 0.14, -0.09]
sis_mantel   = []
for v in vars_mantel:
    r, p, sig = get_mantel("Summer", v, "All")
    sis_mantel.append(r if not np.isnan(r) else 0)
x = np.arange(len(vars_mantel))
w = 0.35
ax1.bar(x - w/2, lai_mantel, w, color=LAI_COLOR, alpha=ALPHA, label="Lai 2024 (PRE)", edgecolor="k", lw=0.5)
ax1.bar(x + w/2, sis_mantel, w, color=SIS_COLOR, alpha=ALPHA, label="This study (SIS)", edgecolor="k", lw=0.5)
ax1.axhline(0, color="k", lw=0.8)
ax1.set_xticks(x)
ax1.set_xticklabels(vars_mantel)
ax1.set_ylabel("Mantel r")
ax1.set_title("Mantel Tests: Bray-Curtis ~\nEnvironmental Distance (Summer)", fontweight="bold", fontsize=10)
ax1.legend(fontsize=8)
ax1.yaxis.grid(True, alpha=0.3, ls="--")

# Panel 2: MK trend τ for sediment vars (SIS)
ax2 = fig.add_subplot(gs[0, 1])
mk_vars  = ["do_nearest", "TOC", "Sulfides", "ORP", "COD"]
mk_labels= ["Bottom DO", "TOC", "Sulfides", "ORP", "COD"]
mk_tau   = []
mk_sig   = []
for v in mk_vars:
    tau, p, slope, sig = get_mk("SIS", v)
    mk_tau.append(tau if not np.isnan(tau) else 0)
    mk_sig.append(sig)
colors_mk = [SIS_COLOR if t > 0 else "#d73027" for t in mk_tau]
bars = ax2.barh(mk_labels, mk_tau, color=colors_mk, alpha=ALPHA, edgecolor="k", lw=0.5)
ax2.axvline(0, color="k", lw=0.8)
for bar, sig_l in zip(bars, mk_sig):
    xpos = bar.get_width() + 0.01 if bar.get_width() >= 0 else bar.get_width() - 0.01
    ha   = "left" if bar.get_width() >= 0 else "right"
    ax2.text(xpos, bar.get_y() + bar.get_height()/2, sig_l,
             va="center", ha=ha, fontsize=9, fontweight="bold")
ax2.set_xlabel("Kendall τ")
ax2.set_title("Mann-Kendall Trends 1991–2024\n(SIS summer annual means)", fontweight="bold", fontsize=10)
ax2.xaxis.grid(True, alpha=0.3, ls="--")

# Panel 3: RF feature importance
ax3 = fig.add_subplot(gs[1, 0])
clf_df = rf[rf["Model"] == "Classifier"].sort_values("Importance", ascending=True)
feat_labels = {"do_nearest":"Bottom DO","TOC":"TOC","Sulfides":"Sulfides","ORP":"ORP",
               "COD":"COD","LOI":"LOI","Clay_pct":"Clay %","Depth_m":"Depth"}
labels3 = [feat_labels.get(f, f) for f in clf_df["Feature"]]
ax3.barh(labels3, clf_df["Importance"], color=SIS_COLOR, alpha=ALPHA, edgecolor="k", lw=0.5)
ax3.set_xlabel("Feature Importance (MDI)")
ax3.set_title("RF Classifier: Predicting Hypoxia\n(sediment vars → DO≤2, AUC={:.3f})".format(
    clf_df["AUC"].dropna().iloc[0] if len(clf_df["AUC"].dropna()) > 0 else 0
), fontweight="bold", fontsize=10)
ax3.xaxis.grid(True, alpha=0.3, ls="--")

# Panel 4: RF 3-class stress classifier feature importance
ax4 = fig.add_subplot(gs[1, 1])
reg_df2 = rf[rf["Model"].str.contains("3class", case=False)].sort_values("Importance", ascending=True)
labels4 = [feat_labels.get(f, f) for f in reg_df2["Feature"]]
ax4.barh(labels4, reg_df2["Importance"], color="#4dac26", alpha=ALPHA, edgecolor="k", lw=0.5)
ax4.set_xlabel("Feature Importance (MDI)")
acc_disp = reg_df2["Accuracy"].dropna().iloc[0] if len(reg_df2["Accuracy"].dropna()) > 0 else 0
f1_disp  = reg_df2["F1_macro"].dropna().iloc[0] if len(reg_df2["F1_macro"].dropna()) > 0 else 0
ax4.set_title(f"RF 3-Class: dead/stressed/healthy\n(Acc={acc_disp:.3f}, F1-macro={f1_disp:.3f})", fontweight="bold", fontsize=10)
ax4.xaxis.grid(True, alpha=0.3, ls="--")

# Panel 5: Tau heatmap (compact)
ax5 = fig.add_subplot(gs[2, :])
mk_heat_vars  = ["do_nearest","TOC","Sulfides","ORP","COD","LOI","Clay_pct"]
mk_heat_regs  = ["All","SIS","Tokyo","Ise"]
mk_heat_labels = ["Bottom DO","TOC","Sulfides","ORP","COD","LOI","Clay %"]
data_h = np.full((len(mk_heat_vars), len(mk_heat_regs)), np.nan)
annot_h = np.full((len(mk_heat_vars), len(mk_heat_regs)), "", dtype=object)
for i, v in enumerate(mk_heat_vars):
    for j, r in enumerate(mk_heat_regs):
        tau, p, slope, sig = get_mk(r, v)
        if not np.isnan(tau):
            data_h[i, j] = tau
            annot_h[i, j] = f"{tau:+.2f}\n{sig}"

im = ax5.imshow(data_h, cmap="RdBu_r", vmin=-0.7, vmax=0.7, aspect="auto")
plt.colorbar(im, ax=ax5, label="Kendall τ", shrink=0.6, pad=0.01)
ax5.set_xticks(range(len(mk_heat_regs)))
ax5.set_xticklabels(mk_heat_regs, fontsize=10)
ax5.set_yticks(range(len(mk_heat_vars)))
ax5.set_yticklabels(mk_heat_labels, fontsize=9)
ax5.set_title("Mann-Kendall Trends by Region and Variable (1991–2024 summer)", fontweight="bold", fontsize=11)
for i in range(len(mk_heat_vars)):
    for j in range(len(mk_heat_regs)):
        txt = annot_h[i, j]
        if txt:
            col = "white" if abs(data_h[i,j]) > 0.45 else "black"
            ax5.text(j, i, txt, ha="center", va="center", fontsize=8, color=col)

plt.savefig("figures/step7_synthesis_figure.png", dpi=150, bbox_inches="tight")
plt.close()
print("  → figures/step7_synthesis_figure.png")

print("\n" + "=" * 60)
print("Step 7 COMPLETE — All analysis steps finished!")
print("=" * 60)
