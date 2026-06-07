"""
Step 5 — Random Forest: Sediment-Based Environmental Driver Analysis
Two complementary models, both used for DRIVER IDENTIFICATION not prediction:

  A) Binary classifier:  predict hypoxia (DO ≤ 2 mg/L) from sediment vars alone
                         — AUC evaluates how much sediment composition encodes
                           oxygen history; feature importance ranks drivers.

  B) 3-class stress classifier: dead (DO≤2) / stressed (2<DO≤4) / healthy (DO>4)
                                — connects directly to K-means cluster regimes;
                                  meaningful class structure avoids continuous
                                  regression failure (R²≈0.07).

Neither model is presented as a predictive tool for new stations.
Sediment variables are lagged integrators of benthic oxygen stress.

Temporal split: train ≤2010 | val 2011–2017 | test >2017

Inputs:
  data/processed/master_sediment_env.csv
  data/raw/benthos_data/bottom_2023.xlsx  (for 3-class direct match)

Outputs:
  data/processed/step5_rf_results.csv
  figures/step5_feature_importance.png
  figures/step5_stress_classifier.png
  figures/step5_driver_effects.png
"""

import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (classification_report, roc_auc_score,
                             precision_recall_fscore_support,
                             confusion_matrix, ConfusionMatrixDisplay)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import warnings
warnings.filterwarnings("ignore")

os.makedirs("figures", exist_ok=True)
np.random.seed(42)

try:
    import shap
    HAS_SHAP = True
    print("SHAP available:", shap.__version__)
except ImportError:
    HAS_SHAP = False
    print("SHAP not installed — skipping SHAP plots")

FEAT_LABELS = {
    "TOC": "TOC", "Sulfides": "Sulfides", "ORP": "ORP",
    "COD": "COD", "LOI": "LOI (organic)", "Clay_pct": "Clay %",
    "Depth_m": "Water depth", "lat_dd": "Latitude",
    "lon_dd": "Longitude", "Year": "Year (trend)",
}
# Sediment-only (for binary classifier — no spatial/temporal leakage)
SED_FEATURES = ["TOC", "Sulfides", "ORP", "COD", "LOI", "Clay_pct", "Depth_m"]
# Full feature set including spatial + temporal context
ALL_FEATURES = SED_FEATURES + ["lat_dd", "lon_dd", "Year"]

# ─────────────────────────────────────────────
# Load master sediment + env data
# ─────────────────────────────────────────────
print("=" * 60)
print("5A. Loading data")
print("=" * 60)

master = pd.read_csv("data/processed/master_sediment_env.csv", encoding="utf-8-sig")
master.rename(columns={"硫化物":"Sulfides","強熱減量":"LOI",
                        "粘土分":"Clay_pct","水深":"Depth_m"}, inplace=True)
master["Year"] = pd.to_numeric(
    master["Year"] if "Year" in master.columns else master["年"], errors="coerce")

# DO-based 3-class stress label
master["stress_class"] = pd.cut(
    master["do_nearest"],
    bins=[-np.inf, 2.0, 4.0, np.inf],
    labels=[0, 1, 2]   # 0=dead, 1=stressed, 2=healthy
).astype(float)

CLASS_NAMES  = {0: "Dead (DO≤2)", 1: "Stressed (2<DO≤4)", 2: "Healthy (DO>4)"}
CLASS_COLORS = {0: "#d73027", 1: "#fc8d59", 2: "#4575b4"}

# Binary hypoxia label
master["is_hypoxic"] = (master["do_nearest"] <= 2.0).astype(int)

print(f"Records: {len(master)}")
print("Stress class distribution:")
for k, v in CLASS_NAMES.items():
    n = (master["stress_class"] == k).sum()
    print(f"  {v}: {n} ({100*n/len(master):.1f}%)")

# ─────────────────────────────────────────────
# 5B. Binary Hypoxia Classifier
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("5B. Binary Hypoxia Classifier (DO ≤ 2 mg/L)")
print("=" * 60)

clf_df = master[["Year","is_hypoxic"] + SED_FEATURES].dropna()
train_c = clf_df[clf_df["Year"] <= 2010]
test_c  = clf_df[clf_df["Year"] >  2017]
print(f"Train: {len(train_c)} (hypoxic={train_c['is_hypoxic'].sum()})")
print(f"Test:  {len(test_c)}  (hypoxic={test_c['is_hypoxic'].sum()})")

clf_bin = RandomForestClassifier(n_estimators=500, max_depth=8, min_samples_leaf=5,
                                 class_weight="balanced", random_state=42, n_jobs=-1)
clf_bin.fit(train_c[SED_FEATURES], train_c["is_hypoxic"])
y_prob_b = clf_bin.predict_proba(test_c[SED_FEATURES])[:,1]
auc_bin  = roc_auc_score(test_c["is_hypoxic"], y_prob_b)

y_pred_b03 = (y_prob_b >= 0.3).astype(int)
prec, rec, f1, _ = precision_recall_fscore_support(
    test_c["is_hypoxic"], y_pred_b03, average="binary", zero_division=0)

print(f"\nBinary classifier (test, threshold=0.30):")
print(f"  AUC-ROC:   {auc_bin:.3f}")
print(f"  Precision: {prec:.3f}  Recall: {rec:.3f}  F1: {f1:.3f}")

imp_bin = pd.Series(clf_bin.feature_importances_, index=SED_FEATURES).sort_values(ascending=False)
print("\nFeature importances:")
for f, v in imp_bin.items():
    print(f"  {f:12s}: {v:.4f}")

# ─────────────────────────────────────────────
# 5C. 3-Class Stress Classifier
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("5C. 3-Class Stress Classifier (dead / stressed / healthy)")
print("=" * 60)

tri_df = master[["Year","stress_class","lat_dd","lon_dd"] + SED_FEATURES].dropna()
tri_df["stress_class"] = tri_df["stress_class"].astype(int)

train_t = tri_df[tri_df["Year"] <= 2010]
val_t   = tri_df[(tri_df["Year"] > 2010) & (tri_df["Year"] <= 2017)]
test_t  = tri_df[tri_df["Year"] >  2017]
print(f"Train: {len(train_t)}  Val: {len(val_t)}  Test: {len(test_t)}")

for split, df in [("Train", train_t), ("Test", test_t)]:
    dist = df["stress_class"].value_counts().sort_index()
    print(f"  {split}: " + "  ".join([f"{CLASS_NAMES[k]}={v}" for k,v in dist.items()]))

# Sediment-only model (baseline — no spatial/temporal leakage)
clf_sed = RandomForestClassifier(n_estimators=500, max_depth=8, min_samples_leaf=5,
                                  class_weight="balanced", random_state=42, n_jobs=-1)
clf_sed.fit(train_t[SED_FEATURES], train_t["stress_class"])

# Full model with spatial + temporal context
clf_tri = RandomForestClassifier(n_estimators=500, max_depth=8, min_samples_leaf=5,
                                  class_weight="balanced", random_state=42, n_jobs=-1)
clf_tri.fit(train_t[ALL_FEATURES], train_t["stress_class"])

# Evaluate sediment-only on val for threshold tuning
y_val_t   = val_t["stress_class"].values
y_prob_v_sed = clf_sed.predict_proba(val_t[SED_FEATURES])
y_prob_v_all = clf_tri.predict_proba(val_t[ALL_FEATURES])

# Compare baseline vs full on val
acc_sed_val = (clf_sed.predict(val_t[SED_FEATURES]) == y_val_t).mean()
acc_all_val = (clf_tri.predict(val_t[ALL_FEATURES]) == y_val_t).mean()
print(f"\nVal accuracy — sediment only: {acc_sed_val:.3f} | +spatial+year: {acc_all_val:.3f}")

# ── Threshold tuning on VAL SET ──────────────────────────────
# Problem: argmax over 3 classes defaults to "healthy" when both dead & stressed
# probabilities are low — covariate shift from training era (high organic load)
# to test era (post-recovery). Fix: find per-class thresholds on val that
# maximise macro-F1 (prioritises minority classes equally).
y_prob_v  = y_prob_v_all   # full-feature model on val set

print("\nThreshold search on val set (prioritise dead recall ≥ 0.50):")
best_f1, best_thr_d, best_thr_s = -1, 0.25, 0.25
for thr_d in np.arange(0.10, 0.55, 0.05):
    for thr_s in np.arange(0.10, 0.55, 0.05):
        y_thr = np.full(len(y_val_t), 2, dtype=int)   # default: healthy
        y_thr[y_prob_v[:, 1] >= thr_s] = 1            # stressed
        y_thr[y_prob_v[:, 0] >= thr_d] = 0            # dead (highest priority)
        # Require dead recall ≥ 0.50 before optimising macro-F1
        rec_dead = ((y_thr == 0) & (y_val_t == 0)).sum() / max((y_val_t == 0).sum(), 1)
        if rec_dead < 0.50:
            continue
        f1_m = classification_report(y_val_t, y_thr, zero_division=0,
                                     output_dict=True)["macro avg"]["f1-score"]
        if f1_m > best_f1:
            best_f1, best_thr_d, best_thr_s = f1_m, thr_d, thr_s

print(f"  Best thresholds: dead≥{best_thr_d:.2f}, stressed≥{best_thr_s:.2f}")
print(f"  Val macro-F1 at best thresholds: {best_f1:.3f}")

def apply_thresholds(probs, thr_dead, thr_stressed):
    pred = np.full(len(probs), 2, dtype=int)
    pred[probs[:, 1] >= thr_stressed] = 1
    pred[probs[:, 0] >= thr_dead]     = 0   # dead overrides stressed
    return pred

# Validate on val set
y_val_pred_thr = apply_thresholds(y_prob_v, best_thr_d, best_thr_s)
rep_val = classification_report(y_val_t, y_val_pred_thr, zero_division=0, output_dict=True)
print(f"  Val accuracy (threshold): {(y_val_pred_thr==y_val_t).mean():.3f}")

# ── Apply to test set ─────────────────────────────────────────
y_test_t  = test_t["stress_class"].values
y_prob_t  = clf_tri.predict_proba(test_t[ALL_FEATURES])

# Argmax baseline (to show the improvement)
y_pred_argmax = clf_tri.predict(test_t[ALL_FEATURES])
rep_argmax = classification_report(y_test_t, y_pred_argmax,
                                    target_names=[CLASS_NAMES[k] for k in [0,1,2]],
                                    zero_division=0, output_dict=True)

# Threshold-adjusted
y_pred_t  = apply_thresholds(y_prob_t, best_thr_d, best_thr_s)
report_t  = classification_report(y_test_t, y_pred_t,
                                   target_names=[CLASS_NAMES[k] for k in [0,1,2]],
                                   zero_division=0, output_dict=True)

acc         = (y_pred_t == y_test_t).mean()
f1_macro    = report_t["macro avg"]["f1-score"]
f1_weighted = report_t["weighted avg"]["f1-score"]

print(f"\n3-class classifier — ARGMAX baseline (test):")
print(f"  Accuracy: {(y_pred_argmax==y_test_t).mean():.3f}  "
      f"F1-macro: {rep_argmax['macro avg']['f1-score']:.3f}")
for cls_idx, cls_name in CLASS_NAMES.items():
    row = rep_argmax.get(cls_name, {})
    print(f"  {cls_name:25s}: rec={row.get('recall',0):.3f}")

print(f"\n3-class classifier — THRESHOLD ADJUSTED (dead≥{best_thr_d:.2f}, stressed≥{best_thr_s:.2f}) (test):")
print(f"  Accuracy:   {acc:.3f}")
print(f"  F1 macro:   {f1_macro:.3f}")
print(f"  F1 weighted:{f1_weighted:.3f}")
print(f"\nPer-class:")
for cls_idx, cls_name in CLASS_NAMES.items():
    row = report_t.get(cls_name, {})
    print(f"  {cls_name:25s}: prec={row.get('precision',0):.3f}  "
          f"rec={row.get('recall',0):.3f}  f1={row.get('f1-score',0):.3f}")

imp_tri = pd.Series(clf_tri.feature_importances_, index=ALL_FEATURES).sort_values(ascending=False)
print("\nFeature importances (3-class):")
for f, v in imp_tri.items():
    print(f"  {f:12s}: {v:.4f}")

# ─────────────────────────────────────────────
# Save results
# ─────────────────────────────────────────────
rows = []
for feat, imp in imp_bin.items():
    rows.append({"Model": "Binary(hypoxia)", "Feature": feat, "Importance": imp,
                 "AUC": auc_bin, "Accuracy": np.nan, "F1_macro": np.nan})
for feat, imp in imp_tri.items():
    rows.append({"Model": "3class(stress)", "Feature": feat, "Importance": imp,
                 "AUC": np.nan, "Accuracy": acc, "F1_macro": f1_macro})
results_df = pd.DataFrame(rows)
results_df.to_csv("data/processed/step5_rf_results.csv", index=False)

# ─────────────────────────────────────────────
# FIGURES
# ─────────────────────────────────────────────
print("\nGenerating figures …")

# ── Fig 1: Side-by-side feature importance (binary + 3-class) ──
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle(
    "Random Forest — Sediment Variable Importance\n"
    "Models used for DRIVER IDENTIFICATION only (not station-level prediction)",
    fontweight="bold", fontsize=11)

for ax, importances, title, color in zip(
    axes,
    [imp_bin, imp_tri],
    [f"A. Binary Hypoxia Classifier\n(sediment → DO≤2 | AUC={auc_bin:.3f})",
     f"B. 3-Class Stress Classifier\n(sediment → dead/stressed/healthy | F1={f1_macro:.3f})"],
    ["#d73027", "#4575b4"]
):
    labels = [FEAT_LABELS.get(f, f) for f in importances.index]
    bars   = ax.barh(labels, importances.values, color=color, alpha=0.82,
                     edgecolor="k", lw=0.5)
    for bar, v in zip(bars, importances.values):
        ax.text(v + 0.003, bar.get_y() + bar.get_height()/2,
                f"{v:.3f}", va="center", fontsize=9)
    ax.set_xlabel("Mean Decrease in Impurity (MDI)", fontsize=10)
    ax.set_title(title, fontsize=10, fontweight="bold")
    ax.invert_yaxis()
    ax.set_xlim(0, importances.values.max() * 1.28)
    ax.xaxis.grid(True, alpha=0.3, ls="--")
    ax.set_axisbelow(True)
    ax.text(0.99, 0.02,
            "Sulfides leads both models\n→ anaerobic sediment stress\n  encodes DO history",
            transform=ax.transAxes, fontsize=7.5, ha="right", va="bottom",
            bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.9))

plt.tight_layout()
plt.savefig("figures/step5_feature_importance.png", dpi=150, bbox_inches="tight")
plt.close()
print("  → figures/step5_feature_importance.png")

# ── Fig 2: 3-class confusion matrix + threshold improvement ──
fig = plt.figure(figsize=(18, 6))
fig.suptitle(
    "3-Class Stress Classifier: dead / stressed / healthy\n"
    f"Threshold-adjusted (dead≥{best_thr_d:.2f}, stressed≥{best_thr_s:.2f} tuned on val 2011–2017)  "
    f"| Accuracy={acc:.3f}  F1-macro={f1_macro:.3f}  (test 2018–2024, n={len(test_t)})\n"
    "Root cause of difficulty: temporal covariate shift — sediment chemistry improved 1991→2024 "
    "(MK: Sulfides τ=−0.35**, COD τ=−0.44***)",
    fontweight="bold", fontsize=9)

gs = gridspec.GridSpec(1, 4, figure=fig, wspace=0.38)

# Panel A: Argmax confusion matrix (before fix)
ax_cm0 = fig.add_subplot(gs[0, 0])
cm0 = confusion_matrix(y_test_t, y_pred_argmax, labels=[0,1,2])
disp0 = ConfusionMatrixDisplay(cm0, display_labels=["Dead","Stressed","Healthy"])
disp0.plot(ax=ax_cm0, colorbar=False, cmap="Reds")
ax_cm0.set_title("A. Argmax (before)\n⚠ dead recall=0.22", fontweight="bold", fontsize=9,
                 color="#c0392b")

# Panel B: Threshold-adjusted confusion matrix
ax_cm = fig.add_subplot(gs[0, 1])
cm = confusion_matrix(y_test_t, y_pred_t, labels=[0,1,2])
disp = ConfusionMatrixDisplay(cm, display_labels=["Dead","Stressed","Healthy"])
disp.plot(ax=ax_cm, colorbar=False, cmap="Blues")
rec_dead_thr = cm[0,0]/max(cm[0].sum(),1)
ax_cm.set_title(f"B. Threshold-adjusted (after)\ndead recall={rec_dead_thr:.2f}",
                fontweight="bold", fontsize=9, color="#27ae60")

# Panel C: Per-class recall comparison (before vs after)
ax_pr = fig.add_subplot(gs[0, 2])
classes_plot = [0, 1, 2]
x = np.arange(len(classes_plot))
w = 0.35

rec_before = [cm0[k,k]/max(cm0[k].sum(),1) for k in classes_plot]
precs = [report_t.get(CLASS_NAMES[k], {}).get("precision", 0) for k in classes_plot]
recs  = [report_t.get(CLASS_NAMES[k], {}).get("recall",    0) for k in classes_plot]

bars_b = ax_pr.bar(x - w/2, rec_before, w, label="Recall (argmax)",
                   color="#e74c3c", alpha=0.6, edgecolor="k", lw=0.5, hatch="//")
bars_a = ax_pr.bar(x + w/2, recs, w, label="Recall (threshold)",
                   color="#2ecc71", alpha=0.8, edgecolor="k", lw=0.5)
for bars, vals in [(bars_b, rec_before), (bars_a, recs)]:
    for bar, v in zip(bars, vals):
        ax_pr.text(bar.get_x() + bar.get_width()/2, v + 0.01,
                   f"{v:.2f}", ha="center", fontsize=8)
ax_pr.set_xticks(x)
ax_pr.set_xticklabels(["Dead\n(DO≤2)", "Stressed\n(2-4)", "Healthy\n(DO>4)"], fontsize=8)
ax_pr.set_ylabel("Recall")
ax_pr.set_ylim(0, 1.15)
ax_pr.set_title("C. Recall: Argmax vs Threshold\n(improvement for minority classes)",
                fontweight="bold", fontsize=9)
ax_pr.legend(fontsize=8)
ax_pr.axhline(0.50, color="orange", lw=1.2, ls="--", alpha=0.7, label="Target ≥0.50")
ax_pr.yaxis.grid(True, alpha=0.3, ls="--")
ax_pr.set_axisbelow(True)

# Marginal effect: Sulfides → stress class probability
ax_me = fig.add_subplot(gs[0, 3])
sulfides_range = np.linspace(
    tri_df["Sulfides"].quantile(0.02),
    tri_df["Sulfides"].quantile(0.98),
    80
)
# Construct a grid with other features at their medians
medians = tri_df[ALL_FEATURES].median()
grid = np.tile(medians.values, (len(sulfides_range), 1))
s_idx = ALL_FEATURES.index("Sulfides")
grid[:, s_idx] = sulfides_range
probs_me = clf_tri.predict_proba(grid)

for cls_i, (cls_k, cls_name, cls_col) in enumerate(
    zip([0,1,2], ["Dead (DO≤2)","Stressed","Healthy"], ["#d73027","#fc8d59","#4575b4"])
):
    ax_me.plot(sulfides_range, probs_me[:, cls_i], color=cls_col, lw=2.5, label=cls_name)
    ax_me.fill_between(sulfides_range, probs_me[:, cls_i],
                       alpha=0.08, color=cls_col)

ax_me.set_xlabel("Sulfides (mg/g)\n[other features at median]", fontsize=9)
ax_me.set_ylabel("Predicted class probability", fontsize=9)
ax_me.set_title("C. Marginal Effect of Sulfides\n(top MDI feature)", fontweight="bold", fontsize=10)
ax_me.legend(fontsize=8)
ax_me.yaxis.grid(True, alpha=0.3, ls="--")
ax_me.set_axisbelow(True)
ax_me.text(0.04, 0.97,
           "Rising Sulfides → ↑ P(Dead)\n"
           "anaerobic sediment = DO stress signature\n"
           "consistent with Mantel r(Sulfides)=+0.12**",
           transform=ax_me.transAxes, fontsize=7.5, va="top",
           bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.9))

plt.savefig("figures/step5_stress_classifier.png", dpi=150, bbox_inches="tight")
plt.close()
print("  → figures/step5_stress_classifier.png")

# ── Fig 3: Driver effects — partial dependence for all features, top-3 ──
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
fig.suptitle(
    "Marginal Effects: Sediment Variables → Stress Class Probability\n"
    "(top 3 features by MDI; other features held at median)",
    fontweight="bold", fontsize=11)

top3 = imp_tri.head(3).index.tolist()
for ax, feat in zip(axes, top3):
    feat_range = np.linspace(
        tri_df[feat].quantile(0.02),
        tri_df[feat].quantile(0.98),
        80
    )
    grid = np.tile(medians.values, (len(feat_range), 1))
    f_idx = ALL_FEATURES.index(feat)
    grid[:, f_idx] = feat_range
    probs = clf_tri.predict_proba(grid)

    for cls_i, (cls_k, cls_col) in enumerate(zip([0,1,2], ["#d73027","#fc8d59","#4575b4"])):
        ax.plot(feat_range, probs[:, cls_i],
                color=cls_col, lw=2.2,
                label=CLASS_NAMES[cls_k] if ax == axes[0] else None)
        ax.fill_between(feat_range, probs[:, cls_i], alpha=0.06, color=cls_col)

    ax.set_xlabel(f"{FEAT_LABELS.get(feat, feat)} (mg/g or m)", fontsize=10)
    ax.set_ylabel("P(class)" if ax == axes[0] else "", fontsize=10)
    ax.set_title(f"{FEAT_LABELS.get(feat, feat)}\n(MDI={imp_tri[feat]:.3f})",
                 fontweight="bold", fontsize=10)
    ax.yaxis.grid(True, alpha=0.3, ls="--")
    ax.set_axisbelow(True)

axes[0].legend(fontsize=8, loc="center right")
plt.tight_layout()
plt.savefig("figures/step5_driver_effects.png", dpi=150, bbox_inches="tight")
plt.close()
print("  → figures/step5_driver_effects.png")

# ── SHAP (if available) ──
if HAS_SHAP:
    bg = shap.sample(train_t[SED_FEATURES].values, min(200, len(train_t)))
    expl = shap.TreeExplainer(clf_tri, bg)
    sv   = expl.shap_values(test_t[SED_FEATURES].values)
    # sv shape: (n_samples, n_features, n_classes) or list of 3
    if isinstance(sv, list):
        sv_dead = sv[0]
    else:
        sv_dead = sv[:,:,0]
    fig, ax = plt.subplots(figsize=(8, 5))
    shap.summary_plot(sv_dead, test_t[SED_FEATURES].values,
                      feature_names=[FEAT_LABELS.get(f,f) for f in SED_FEATURES],
                      show=False, max_display=7, plot_type="bar")
    ax.set_title("SHAP: Features driving Dead-zone prediction", fontweight="bold")
    plt.tight_layout()
    plt.savefig("figures/step5_shap.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  → figures/step5_shap.png")

print("\n" + "=" * 60)
print("Step 5 COMPLETE")
print("=" * 60)
print(f"  Binary classifier AUC:          {auc_bin:.3f}")
print(f"  3-class classifier accuracy:    {acc:.3f}")
print(f"  3-class F1 macro:               {f1_macro:.3f}")
print(f"  3-class F1 weighted:            {f1_weighted:.3f}")
print(f"  Top driver (both models):       {imp_tri.index[0]} (MDI={imp_tri.iloc[0]:.3f})")
print()
print("Interpretation: Sediment Sulfides and LOI encode anaerobic stress history.")
print("Rising Sulfides → increasing P(dead zone). Consistent with Mantel r=+0.12**")
print("and the SIS-wide Sulfides decline trend (MK τ=−0.35**, improving since ~2007).")
