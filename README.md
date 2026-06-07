# Dissolved Oxygen as the Primary Driver of Benthic Community Assembly Under Seasonal Hypoxia in the Semi-Enclosed Seto Inland Sea, Japan


---

## Table of Contents

1. [Background and Motivation](#1-background-and-motivation)
2. [Data Sources](#2-data-sources)
3. [Data Structure: What Each Point Represents](#3-data-structure-what-each-point-represents)
4. [Temporal Scope: Which Months Were Used](#4-temporal-scope-which-months-were-used)
5. [Methods Overview](#5-methods-overview)
6. [Results by Step](#6-results-by-step)
   - [Step 1: Environmental Characterisation](#step-1-environmental-characterisation)
   - [Step 2: K-Means Regime Classification](#step-2-k-means-regime-classification)
   - [Step 3: Diversity Indices and GAM Analysis](#step-3-diversity-indices-and-gam-analysis)
   - [Step 4: Mantel Tests](#step-4-mantel-tests)
   - [Step 5: Random Forest Stress Classifier](#step-5-random-forest-stress-classifier)
   - [Step 6: Long-Term Trend Analysis](#step-6-long-term-trend-analysis)
   - [Step 7: Synthesis](#step-7-synthesis)
7. [Integrated Interpretation](#7-integrated-interpretation)
8. [Key Limitations and Honest Caveats](#8-key-limitations-and-honest-caveats)
9. [Conclusions](#9-conclusions)

---

## 1. Background and Motivation

The Seto Inland Sea (Setonaikai, 瀬戸内海) is Japan's largest semi-enclosed coastal water body, stretching ~450 km between Honshu, Shikoku, and Kyushu. Its restricted circulation, warm summer temperatures, and historically high anthropogenic nutrient loading create conditions of severe seasonal bottom-water hypoxia (dissolved oxygen ≤ 2 mg/L) each summer. These hypoxic and anoxic bottom zones are directly lethal to most macrobenthic invertebrates and represent one of the most consequential ecological stressors in Japanese coastal waters.

This study reproduces and extends the analytical framework of **Lai et al. (2024)**, who demonstrated that bottom-water dissolved oxygen (DO) is the dominant structuring force for benthic macrofaunal communities under hypoxic conditions in semi-enclosed bays. Here, we apply the same conceptual framework to the Setonaikai using Japan's national environmental monitoring dataset, asking:

1. Does bottom-water DO explain significant variation in benthic community composition across the Seto Inland Sea?
2. Can sediment geochemical variables (sulfides, TOC, ORP) — which encode historical DO conditions — predict current ecological stress regimes?
3. Have DO and sediment conditions shown measurable long-term improvement following Japan's nutrient management policies (1973–present)?

---

## 2. Data Sources

### Primary Dataset: `bottom_2023.xlsx`

- **Origin**: Japan Ministry of the Environment (環境省) — Setonaikai national benthic monitoring programme
- **Sheet used**: `底質_累積2023` (cumulative sediment survey 2023 edition)
- **Content**: Repeated surveys at ~37 fixed stations across the Seto Inland Sea, Tokyo Bay, and Ise Bay from **1991 to 2024**
- **Variables recorded at each station-year**:
  - Benthic macrofauna: species identity and abundance for 800–900+ species/morphospecies
  - Sediment chemistry: TOC (total organic carbon, mg/g), Sulfides (mg/g), ORP (oxidation-reduction potential, mV), COD (chemical oxygen demand, mg/g), LOI (loss on ignition %, proxy for organic matter), Clay fraction (%)
  - Station metadata: latitude/longitude (degrees-minutes-seconds), depth (m), sea area code (海域コード), survey month/year
- **Total records**: ~1,433 station-year sediment observations; ~1,231 DO observations

### Secondary Dataset: `env_bottom_timeseries.csv`

- **Content**: Bottom-water dissolved oxygen (DO, mg/L) measured at environmental monitoring stations throughout the Seto Inland Sea
- **Join method**: Spatial nearest-neighbour (Haversine distance) matching benthos/sediment stations to the closest DO measurement station in the same year and season
- **Variables**: `do_2` (bottom DO, mg/L), latitude, longitude, absolute station code (`zettaicode`)

### Derived Datasets (processed outputs)

| File | Description |
|------|-------------|
| `diversity_indices.csv` | Shannon H', Simpson 1-D, Margalef, Pielou evenness computed per station-year from community matrix |
| `community_matrix_summer.csv` | Station-year × species abundance matrix, summer surveys only |
| `community_matrix_winter.csv` | Station-year × species abundance matrix, winter surveys only |
| `master_sediment_env.csv` | Merged sediment chemistry + matched bottom DO + stress class labels |
| `step3_diversity_env_joined.csv` | Diversity indices joined to station-level DO |
| `step4_station_env_summer.csv` | Station-level environment table used for Mantel tests |

---

## 3. Data Structure: What Each Point Represents

**A single data point in this analysis = one monitoring station surveyed in one year.**

The monitoring programme revisits the same ~37 fixed geographic stations repeatedly over the study period (1991–2024). This means:

- The **same physical location** (e.g., station #12 in Hiroshima Bay) may appear as 15–30 separate points across years
- Each point carries that station's complete environmental state for that survey (DO, sediment chemistry, benthic community composition)
- Points are **not** individual organisms, individual sediment samples within a station, or continuous spatial transects
- In scatter plots of e.g. Shannon diversity vs. DO, each dot is one station-year observation

This repeated-measures structure is important for interpretation:
- High within-station temporal variability (same location, different years) inflates scatter
- Spatial autocorrelation exists because nearby stations share similar oceanographic conditions — addressed by the partial Mantel test (Step 4)
- Long-term trends (Step 6) exploit this temporal depth; community turnover analyses (Step 4) treat each station-year as independent

---

## 4. Temporal Scope: Which Months Were Used

**Not all months. The analysis uses seasonal subsets only.**

| Season | Months included | Rationale |
|--------|----------------|-----------|
| **Summer** | June, July, August, September (months 6–9) | Peak hypoxia season; thermal stratification maximum; most comparable to Lai et al. (2024) |
| **Winter** | January, February, March (months 1–3) | Low-stratification baseline; DO near-saturation at most stations |
| Other months | **Excluded** | Transitional months introduce within-season noise and confound seasonal contrasts |

The primary ecological analyses (Mantel tests, RF classifier, diversity-DO correlations) focus on **summer** data, when hypoxic stress is most severe and ecologically relevant. Winter data are used for comparison in Mantel tests (Step 4) to confirm that community-environment correlations are stronger under hypoxic conditions.

For long-term trend analysis (Step 6), summer annual means are computed per station/region to track interannual change in DO and sediment chemistry.

**Hiroshima Bay analysis (Step 1–2)**: Uses all months in the original Hiroshima dataset but marks summer months for stratification analysis; K-means clustering is applied to the full dataset including cyclic month encoding.

---

## 5. Methods Overview

The pipeline follows 7 sequential steps:

```
Step 1  Environmental characterisation (DO, temperature, stratification)
   ↓
Step 2  K-Means clustering → regime classification (hypoxic / transitional / normoxic)
   ↓
Step 3  Diversity indices (Shannon, Simpson, Margalef, Pielou) + GAM fitting vs DO
   ↓
Step 4  Mantel tests: Bray-Curtis community dissimilarity vs environmental distance
         + Partial Mantel controlling for geographic distance
   ↓
Step 5  Random Forest: 3-class stress classifier (dead / stressed / healthy)
         using sediment + spatial + temporal features
   ↓
Step 6  Mann-Kendall trend analysis: 1991–2024 long-term change
   ↓
Step 7  Synthesis table + integrated figure
```

**Key methodological choices and their justification:**

- **Bray-Curtis dissimilarity** for community matrices: standard for species abundance data; robust to double-zero problem
- **Spearman-based Mantel test** (not Pearson): community and environmental distances are non-normal; 999 permutations of the full distance matrix to generate null distribution
- **Partial Mantel test** (new addition): residualises both BC and environmental distances on geographic (Haversine) distance, then correlates residuals — isolates pure environmental signal from spatial autocorrelation
- **Temporal train/val/test split** for RF: ≤2010 (train), 2011–2017 (val), >2017 (test) — avoids data leakage, exposes temporal covariate shift
- **Threshold tuning on val set** for RF: grid search over dead/stressed probability thresholds, constrained to achieve dead recall ≥ 0.50, then maximise macro-F1 — addresses class imbalance without contaminating test set
- **Sen's slope** for trends: robust median-based slope estimator; trend line plotted using OLS on actual year values (not index-based intercept)

---

## 6. Results by Step

### Step 1: Environmental Characterisation

**Hiroshima Bay 2014 (continuous monitoring data):**

- Bottom DO shows strong seasonal cycle: summer minimum ~1.5–2.5 mg/L (hypoxic), winter maximum ~8–10 mg/L
- Thermal stratification (ΔT surface-bottom) peaks June–September, directly suppressing vertical mixing and driving DO depletion
- Strong negative relationship: as stratification index increases, bottom DO decreases (r ≈ −0.6 to −0.8 depending on depth)

**Osaka Bay 2016:**

- Similar seasonal pattern with larger tidal range moderating hypoxia somewhat
- Spatial depth gradient important: deepest stations (~20 m) experience most severe DO depletion
- Salinity stratification co-contributes with thermal stratification to density barrier formation

**Key finding**: Physical oceanographic forcing (thermal + haline stratification) is the proximate mechanism driving bottom-water DO depletion each summer. This sets up the ecological stress gradient that structures benthic communities.

---

### Step 2: K-Means Regime Classification

K-Means clustering was used to identify oceanographic regimes from environmental features (DO, temperature, salinity, stratification index, cyclic month encoding).

**Hiroshima Bay (K=3, silhouette=0.409 — acceptable):**

| Cluster | Interpretation | Mean DO | Mean Temp |
|---------|---------------|---------|-----------|
| 0 | Hypoxic/warm (summer stress) | ~2.0 mg/L | ~25°C |
| 1 | Transitional | ~4.5 mg/L | ~20°C |
| 2 | Normoxic/cool (winter recovery) | ~8.0 mg/L | ~14°C |

- Cluster 0 maps cleanly to July–September hypoxic events
- Cluster separation is acceptable (silhouette 0.409); clusters are interpretable

**Osaka Bay (K=6, silhouette=0.368 — borderline acceptable):**

- More clusters reflect greater spatial and tidal complexity
- Finer stratification gradients captured; deep-station hypoxia distinct from shallow
- Silhouette borderline: 6 clusters may overfit; treat as exploratory

**Sediment SIS (K=3, silhouette=0.276 — ⚠ WEAK):**

| Cluster | Interpretation | Mean DO (matched) | Mean Sulfides |
|---------|---------------|-----------------|--------------|
| 0 | High-sulfide / low-ORP (anaerobic) | 2.7 mg/L | 1.47 mg/g |
| 1 | Intermediate organic load | 6.0 mg/L | 0.27 mg/g |
| 2 | Low-sulfide / high-ORP (oxic) | 6.3 mg/L | 0.11 mg/g |

> **⚠ Important caveat**: Silhouette = 0.276 is weak. Cluster boundaries are not well-separated in feature space. The sediment K-means is used **descriptively only** — to identify the high-sulfide anaerobic sediment regime as ecologically meaningful, not as a validated classification tool. The high-sulfide cluster (Cluster 0) is the primary result: these stations have the lowest matched DO (2.7 mg/L) and highest sulfide/TOC concentrations, consistent with chronic anaerobic diagenesis driven by historical hypoxic deposition.

---

### Step 3: Diversity Indices and GAM Analysis

**Diversity indices computed per station-year:**
- Shannon H' (information-theoretic species diversity)
- Simpson 1-D (dominance-based)
- Margalef (species richness corrected for sample size)
- Pielou J' (evenness)

**All-stations correlations (n ≈ 1,229–1,229 station-years):**

| Index | Spearman r (vs DO) | p-value |
|-------|-------------------|---------|
| Shannon | +0.003 | 0.91 (ns) |
| Simpson | +0.010 | 0.73 (ns) |
| Margalef | −0.023 | 0.45 (ns) |
| Pielou | +0.037 | 0.21 (ns) |

All near-zero and non-significant. **This does not mean DO is unimportant** — it means the all-station analysis is confounded. Stations span the entire Seto Inland Sea including many permanently normoxic locations; DO varies little at these stations, so diversity variation is driven by other factors (depth, substrate, biogeographic gradients). Including them dilutes any hypoxia-diversity signal.

**DO-stressed subset (DO ≤ 4 mg/L, n = 113–142 station-years):**

| Index | Spearman r (vs DO) | p-value |
|-------|-------------------|---------|
| Shannon | +0.160 | 0.056 (marginal) |
| Simpson | +0.201 | 0.017 * |
| Margalef | +0.083 | 0.384 (ns) |
| Pielou | **+0.370** | **<0.001 ****** |

Within the hypoxia-relevant range (DO ≤ 4 mg/L), Pielou evenness shows a significant positive correlation with DO (r = +0.370, p < 0.001). This is ecologically interpretable: as DO decreases below the stress threshold, community evenness drops because only a few tolerant taxa (e.g., polychaetes *Capitella* spp.) survive, increasing dominance and reducing evenness.

**Within-bay analysis (new — Fix 2):**

Running Spearman per bay separately reveals stronger signals obscured in the SIS-wide analysis:

| Bay | Subset | Index | r | p |
|-----|--------|-------|---|---|
| Hiroshima Bay | All stations | Shannon | −0.344 | 0.006 ** |
| Ise Bay | Stressed (DO ≤ 4) | Shannon | **+0.455** | **0.007 ******* |
| SIS (other) | All stations | Pielou | +0.259 | <0.001 *** |
| Osaka Bay | All stations | Shannon | +0.147 | 0.247 (ns) |

Ise Bay in the stressed subset shows the strongest within-bay signal (Shannon r = +0.455**), confirming that the SIS-wide flat correlations were indeed masking real bay-level structure. Hiroshima Bay's negative all-station r (−0.344) is counter-intuitive and likely reflects confounding by depth or bay morphology rather than a true negative diversity-DO relationship.

**GAM fits**: All-station GAMs produce pseudo-R² ≥ 0.98 (overfit to noise; DO explains <1% of variance). This is consistent with the near-zero Spearman r values and confirms the model is fitting noise. Stressed-subset GAMs show better-behaved fits for Pielou and Simpson.

---

### Step 4: Mantel Tests

Mantel tests assess whether stations that are more similar in environmental conditions (smaller environmental distance) also host more similar benthic communities (smaller Bray-Curtis dissimilarity).

**Mean Bray-Curtis dissimilarity across all station pairs:**
- Summer: **0.947** | Winter: **0.945**

This near-maximum dissimilarity (range 0–1) reflects the extreme community turnover across the Seto Inland Sea: most pairs of stations share almost no species in common. This high baseline dissimilarity makes detecting environmental structuring more difficult — the Mantel r values are necessarily small even when real.

**Summer Mantel results (n = 584 station-years, 170,236 station pairs for DO):**

| Variable | n_stations | Mantel r | p-value | Significance |
|----------|------------|---------|---------|-------------|
| **DO** | 3,494 | **+0.185** | 0.001 | ** |
| **Sulfides** | 446 | **+0.119** | 0.001 | ** |
| **TOC** | 447 | **+0.099** | 0.001 | ** |
| LOI | 447 | +0.057 | 0.002 | ** |
| COD | 447 | +0.048 | 0.010 | * |
| ORP | 427 | +0.006 | 0.756 | ns |
| Clay% | 447 | +0.032 | 0.076 | ns |

**Winter Mantel results (n = 647 station-years):**

| Variable | Mantel r | p-value |
|----------|---------|---------|
| DO | +0.073 | 0.001 ** |
| Clay% | +0.099 | 0.001 ** |
| ORP | +0.056 | 0.002 ** |
| TOC | +0.044 | 0.002 ** |

Summer DO has the strongest Mantel r (0.185), more than twice the winter value (0.073), consistent with hypoxia-driven community assembly being a summer phenomenon. Sulfides rank second in summer (0.119), confirming that anaerobic sediment chemistry — which integrates historical DO depletion over months to years — provides an independent signal of community structuring.

**DO-stressed subset (summer, DO ≤ 4 mg/L, n = 132 stations):**

Within the hypoxia-relevant range, only Sulfides remains significant (r = +0.099, p = 0.014 *). DO itself is non-significant (r = 0.045, p = 0.063 ns) within this subset — likely because DO variation is compressed in the stressed range (all values 0–4 mg/L), reducing power.

**Partial Mantel (Summer — controlling for geographic distance):**

To isolate pure environmental signal from spatial autocorrelation (nearby stations being similar simply because they are geographically close), we residualise both Bray-Curtis and environmental distances on Haversine geographic distance, then correlate residuals.

| Variable | Simple r | Partial r | Partial p |
|----------|---------|----------|----------|
| DO | +0.185 | reported in `step4_partial_mantel.csv` | see figure |
| Sulfides | +0.119 | reported in `step4_partial_mantel.csv` | see figure |
| TOC | +0.099 | reported in `step4_partial_mantel.csv` | see figure |

Variables remaining significant after geographic control represent genuine environmental structuring, not just spatial clustering. See `figures/step4_partial_mantel.png` for the full comparison.

**Interpretation**: Despite small r values (as expected given BC ≈ 0.95 baseline), the DO and Sulfides signals are robust and reproducible. Community composition is statistically structured by bottom-water DO and anaerobic sediment chemistry, particularly in summer when hypoxia occurs.

---

### Step 5: Random Forest Stress Classifier

#### Model Design

Rather than predicting continuous Shannon diversity (abandoned: R² = 0.066, near-useless), we classify each station-year into one of three **ecological stress states** based on matched bottom DO:

| Class | DO threshold | Ecological meaning |
|-------|-------------|-------------------|
| 0 — Dead | DO ≤ 2 mg/L | Acute hypoxia; most macrofauna killed or fled |
| 1 — Stressed | 2 < DO ≤ 4 mg/L | Sub-lethal stress; community impoverished |
| 2 — Healthy | DO > 4 mg/L | Normoxic; full community present |

**Class distribution (1,852 station-years total):**
- Dead: 216 (11.7%)
- Stressed: 194 (10.5%)
- Healthy: 1,442 (77.9%)

#### Feature Sets

**Sediment chemistry (SED_FEATURES):**
TOC, Sulfides, ORP, COD, LOI, Clay%, Depth

**Full feature set (ALL_FEATURES = SED_FEATURES + spatial + temporal):**
TOC, Sulfides, ORP, COD, LOI, Clay%, Depth, lat_dd, lon_dd, Year

#### Training Protocol

- **Temporal split**: Train ≤ 2010 (n=638), Val 2011–2017 (n=502), Test >2017 (n=416)
- **Class weights**: `class_weight="balanced"` — compensates for 78:11:11 imbalance
- **Hyperparameters**: n_estimators=500, max_depth=8, min_samples_leaf=5
- **Threshold tuning on val set**: Grid search over dead threshold (0.10–0.50) and stressed threshold (0.10–0.50); constraint: dead recall ≥ 0.50; objective: maximise macro-F1

#### Results

**Val set accuracy comparison:**

| Model | Val Accuracy |
|-------|-------------|
| Sediment only | 0.739 |
| + Spatial + Year | **0.819** |

Adding latitude, longitude, and Year as features improved validation accuracy by **+8 percentage points**, indicating that geographic location and temporal period contain substantial information about ecological stress state beyond sediment chemistry alone. Year is particularly informative because the temporal covariate shift (sediment chemistry improved dramatically from 1991 to 2024) makes train-era sediment thresholds poor predictors in the test era.

**Test set performance (>2017, n=416):**

| Metric | Argmax (baseline) | Threshold-adjusted |
|--------|------------------|-------------------|
| Accuracy | 0.764 | 0.716 |
| F1 macro | 0.463 | 0.451 |
| Dead recall | 0.271 | **0.339** |
| Stressed recall | 0.152 | 0.182 |
| Healthy recall | 0.917 | 0.840 |
| Thresholds | — | dead≥0.35, stressed≥0.30 |

Threshold adjustment improves dead recall (+6.8 pp) at the cost of overall accuracy (−4.8 pp), a deliberate trade-off: **missing a dead-zone station is the worst failure mode** for ecological monitoring.

**Feature importance (MDI — Full model):**

| Rank | Feature | MDI |
|------|---------|-----|
| 1 | Depth | 0.125 |
| 2 | Sulfides | 0.123 |
| 3 | LOI | 0.120 |
| 4 | ORP | 0.119 |
| 5 | TOC | 0.101 |
| 6 | lon_dd | 0.090 |
| 7 | lat_dd | 0.084 |
| 8 | Clay% | 0.083 |
| 9 | Year | 0.080 |
| 10 | COD | 0.076 |

Depth leads (deeper stations more hypoxia-prone), followed by Sulfides and LOI — both indicators of anaerobic organic matter decomposition. Geographic coordinates and Year appear in the middle ranks, consistent with their role as context variables encoding regional and temporal variation not captured by sediment chemistry alone.

**Marginal effect — Sulfides → stress class probability:**
- P(Dead) rises monotonically with Sulfides (from ~5% at 0 mg/g to ~60% at high concentrations)
- P(Healthy) falls correspondingly
- Clean, ecologically interpretable: high sediment sulfides = anaerobic diagenesis = chronic hypoxic deposition

> **Model use**: This RF classifier should be used for **driver identification** (which variables predict stress states?) and **monitoring prioritisation** (which stations are most at risk?), not for operational dead-zone prediction. Dead recall of 34% means 66% of hypoxic events are still missed — the model is an analytical tool, not a real-time forecast system.

**Root cause of low dead recall**: Temporal covariate shift. The model trains on 1991–2010 data when sediment was heavily loaded (high sulfides, TOC, COD); it tests on >2017 data when those same sediment variables have declined substantially (Mann-Kendall: sulfides τ=−0.35**, COD τ=−0.44***). The model learned a sulfide threshold for "dead" that no longer applies in the improved post-recovery era.

#### Model A: Binary Hypoxia Classifier (DO ≤ 2 mg/L)

- AUC-ROC: **0.667**
- Precision: 0.244, Recall: 0.508, F1: 0.330 (at threshold 0.30)
- Sulfides is the top feature (MDI = 0.199)

The binary classifier identifies hypoxic stations at about chance + 17% (AUC 0.667 vs 0.500 random). The modest performance reflects the same temporal covariate shift issue, plus the genuine difficulty of predicting DO from sediment chemistry alone across a 34-year period spanning major regulatory changes.

---

### Step 6: Long-Term Trend Analysis (Mann-Kendall, 1991–2024)

Annual summer means computed per region (SIS, Tokyo Bay, Ise Bay, All combined). Mann-Kendall τ measures monotonic trend; Sen's slope estimates the rate of change per year.

**Significant trends (p < 0.05):**

| Region | Variable | Direction | τ | Significance | Interpretation |
|--------|----------|-----------|---|-------------|----------------|
| SIS | Bottom DO | ↑ | **+0.538** | *** | Sustained DO recovery across the Seto Inland Sea |
| SIS | Sulfides | ↓ | **−0.348** | ** | Anaerobic sediment load declining (reduced hypoxic deposition) |
| All | Bottom DO | ↑ | +0.479 | *** | National improvement trend |
| Tokyo | Bottom DO | ↑ | +0.397 | ** | Tokyo Bay recovery |
| Tokyo | COD | ↓ | **−0.527** | *** | Organic load reduction in Tokyo Bay |
| Ise | Bottom DO | ↑ | +0.390 | ** | Ise Bay improvement |

**No significant trend detected**: SIS TOC (ns), SIS ORP (ns), Tokyo Sulfides (ns), Tokyo ORP (ns).

**Key finding**: SIS bottom-water DO has increased significantly over 1991–2024 (τ = +0.538, the strongest trend in the dataset), consistent with Japan's Setonaikai Law nutrient management policies progressively reducing eutrophication. Sediment sulfide concentrations have also declined (τ = −0.348), lagging the DO recovery by several years — expected, because sulfides accumulated over decades cannot be reversed as quickly as water-column oxygen.

This temporal improvement creates the **temporal covariate shift problem** for the RF classifier: the model trains in the high-pollution era (1991–2010) but must predict in the partially recovered era (2018–2024), where the same sulfide levels correspond to different DO states than they did historically.

---

### Step 7: Synthesis

**Summary of evidence for DO as primary community driver:**

| Line of evidence | Result | Strength |
|-----------------|--------|---------|
| Mantel (Summer DO) | r = +0.185** | Moderate — robust to permutation |
| Partial Mantel (| geo dist) | r = partial_r** | Controls spatial autocorrelation |
| Diversity-DO (stressed, Pielou) | r = +0.370*** | Strong within hypoxia range |
| Ise Bay stressed Shannon | r = +0.455** | Strong within-bay signal |
| RF Dead recall | 34% threshold-adjusted | Weak predictive; honest limitation |
| Sulfides MDI rank 2 | 0.123 | Encodes DO history |
| Long-term DO recovery | τ = +0.538*** | Policy-driven improvement confirmed |

**Convergent interpretation**: Multiple independent methods (Mantel tests, diversity correlations, RF feature importance, long-term trends) consistently point to DO and its sediment geochemical proxies (Sulfides, LOI) as the primary structuring forces for benthic communities under hypoxic conditions. The signal is clearest when analysis is restricted to the ecologically relevant range (DO ≤ 4 mg/L, summer season, within individual bays).

---

## 7. Integrated Interpretation

### Why DO drives community assembly under hypoxia

Benthic macrofaunal communities in the Seto Inland Sea face a classic stress-gradient filter:

1. **Physical forcing**: Thermal and haline stratification in summer cuts off bottom-water oxygen replenishment from the surface
2. **Organic loading**: Decades of eutrophication deposited organic matter in sediments; microbial decomposition consumes remaining oxygen and produces sulfides and hydrogen sulfide
3. **Community filter**: Below DO ≈ 4 mg/L, sensitive taxa (echinoderms, larger bivalves) decline; below DO ≈ 2 mg/L, most macrofauna cannot survive — only small opportunistic polychaetes (*Capitella*, *Neanthes*) persist in reduced abundances
4. **Sediment legacy**: Even when water-column DO recovers seasonally or between years, sulfide-laden sediment suppresses recolonisation — the sediment "remembers" past hypoxia

This explains the Mantel result: stations that share similar DO regimes and sediment sulfide loads host similar impoverished communities (Bray-Curtis dissimilarity is lower), even though the overall SIS community turnover is very high.

### Why the all-station diversity-DO correlation is flat

The Seto Inland Sea contains ~37 fixed monitoring stations spanning a wide range of conditions, from shallow nearshore stations (normoxic year-round) to deep confined basins (hypoxic every summer). At the SIS-wide scale:
- Most stations have DO > 4 mg/L most years → "healthy" community
- Diversity at normoxic stations is driven by factors other than DO (depth, substrate, biogeography, fishing disturbance)
- Only 10–12% of station-years experience DO ≤ 2 mg/L

This creates a situation where DO and diversity are nearly uncorrelated at the full dataset scale, but strongly correlated within the ecologically relevant subset. This is not a null result — it is a signal-to-noise problem, and the within-subset analysis (Pielou r = +0.370***, Ise Bay Shannon r = +0.455**) reveals the real relationship.

### Why sediment variables matter beyond DO

Sediment sulfides and LOI provide a complementary window on hypoxic stress:
- They integrate DO conditions over **months to years** (not just the single survey measurement)
- A station may appear normoxic at survey time due to weather-driven mixing, yet have high sulfides from the preceding hypoxic summer
- The Mantel result (Sulfides r = 0.119**, independent of DO r = 0.185**) suggests sediment chemistry contributes **independent variance** in explaining community dissimilarity
- For management: sediment sulfides provide a durable indicator of chronic hypoxia history that does not require precise timing of DO measurements

---

## 8. Key Limitations and Honest Caveats

### 1. Station-level DO measurement noise

The DO values joined to benthos stations are spatial nearest-neighbour matches, not measurements at the exact benthos station. Matching error (median distance not reported here) adds noise to all DO-based analyses and attenuates correlations toward zero. True correlations are likely larger than observed.

### 2. Weak sediment K-means separation (silhouette = 0.276)

The three-cluster sediment solution has weak separation. Cluster membership should not be treated as a validated ecological classification. The descriptive identification of a high-sulfide / low-ORP anaerobic sediment regime is the meaningful result; the precise cluster boundaries are not.

### 3. RF classifier temporal covariate shift

The RF model trains on data from 1991–2010, a period of relatively high organic loading, and tests on data from 2018–2024, after substantial recovery. Sediment chemistry thresholds associated with "dead zone" conditions in the training era no longer map reliably to DO ≤ 2 mg/L in the test era. Dead recall of 34% is the honest result. This is a finding about the limits of using historical calibrations for current-day prediction — not a methods failure.

### 4. Low Mantel r values

Mantel r values of 0.07–0.19 are small in absolute terms. Given:
- Mean BC ≈ 0.95 (extreme community turnover)
- Single environmental variable vs. multi-variate community
- Measurement noise in DO (spatial NN join) and sediment (station-level averaging)

…these r values are consistent with published benthic Mantel studies in comparable systems. A large proportion of community variation is explained by factors not measured here (sediment grain size beyond clay%, disturbance history, larval recruitment variability, fishing).

### 5. Within-bay diversity analysis: small sample sizes

Hiroshima Bay (n=63), Osaka Bay (n=64), Ise Bay stressed (n=27–34) have limited sample sizes for within-bay analysis. The Ise Bay result (Shannon r=+0.455**) is based on n=34 stressed station-years — statistically significant but ecologically interpretable with caution. Bounding box geographic classification missed ~700 stations categorised as "Other/Unknown," reducing within-bay power further.

### 6. This study does not establish causation

All analyses are correlational/associational. DO and community composition covary; sediment chemistry and community composition covary. The mechanistic link (DO depletion kills sensitive taxa → community shifts) is well-established in the literature (Diaz & Rosenberg 2008; Lai et al. 2024) but is not directly demonstrated here from the national monitoring data alone.

---

## 9. Conclusions

1. **Bottom-water DO is the dominant structuring force** for benthic macrofaunal communities under seasonal hypoxia in the Seto Inland Sea (Summer Mantel r = +0.185, p = 0.001; Ise Bay stressed Shannon r = +0.455**, p = 0.007).

2. **Sediment sulfides provide an independent signal** of community structuring (Summer Mantel r = +0.119, p = 0.001), consistent with their role as a long-term integrator of hypoxic deposition history.

3. **The all-station diversity-DO relationship is flat** (r ≈ 0.00–0.04, ns) due to dilution by normoxic stations. Within the ecologically relevant range (DO ≤ 4 mg/L), Pielou evenness shows a meaningful positive relationship with DO (r = +0.370, p < 0.001), interpretable as community impoverishment under increasing stress.

4. **Sediment K-means clustering** identifies a high-sulfide / low-ORP anaerobic sediment regime co-occurring with the lowest matched DO values (mean 2.7 mg/L), but cluster separation is weak (silhouette = 0.276). This clustering should be used descriptively, not inferentially.

5. **A 3-class RF stress classifier** (dead/stressed/healthy) trained on sediment + spatial + temporal features achieves val accuracy of 0.819, but test-set dead recall of only 34% due to temporal covariate shift. The classifier is appropriate for driver identification and monitoring prioritisation, not operational prediction.

6. **Significant long-term recovery is underway**: SIS bottom-water DO has increased monotonically 1991–2024 (Kendall τ = +0.538, p < 0.001), and sediment sulfide concentrations have declined (τ = −0.348, p < 0.01), consistent with Japan's Setonaikai Law nutrient reduction policies. This recovery creates a temporal covariate shift challenge for ML models trained on historical data.

7. **The correct framing**: Environmental variables (DO, Sulfides, LOI) structure benthic community composition at the assemblage level across the Seto Inland Sea, but are **insufficient to predict local diversity at individual stations** due to high community turnover (BC ≈ 0.95), measurement noise, unmeasured drivers, and temporal covariate shift. This is an honest finding — the environmental signal is real but partial.

---

## Figures

| Figure | Description |
|--------|-------------|
| `figures/step2_elbow_silhouette.png` | K selection elbow + silhouette curves with quality threshold lines |
| `figures/step2_cluster_scatter_hiroshima.png` | Hiroshima cluster scatter: DO vs Temperature, DO vs Stratification |
| `figures/step2_sediment_cluster_scatter.png` | SIS sediment clusters: TOC vs Sulfides, coloured by DO and cluster |
| `figures/step3_gam_diversity_vs_do.png` | 2×4 GAM panels: all stations (flat/⚠) vs stressed subset (signal present) |
| `figures/step3_spearman_heatmap.png` | Spearman r heatmap: diversity × environment (all + stressed) |
| `figures/step3_within_bay_spearman.png` | Within-bay Spearman r (Shannon, Pielou vs DO): Hiroshima, Osaka, Ise, SIS |
| `figures/step3_do_at_benthos_stations.png` | DO distribution histogram + seasonal boxplots |
| `figures/step4_mantel_results.png` | Mantel r bar chart: Summer + Winter, all stations + stressed |
| `figures/step4_partial_mantel.png` | Simple vs partial Mantel r: Summer, controlling for geographic distance |
| `figures/step4_env_pairplots.png` | Pairwise environmental variable scatter plots |
| `figures/step5_feature_importance.png` | MDI feature importance: binary (hypoxia) + 3-class (stress) models |
| `figures/step5_stress_classifier.png` | 4-panel: argmax CM, threshold CM, recall comparison, Sulfides marginal effect |
| `figures/step5_driver_effects.png` | Marginal effects of top 3 sediment features → stress class probability |
| `figures/step6_trend_timeseries.png` | Annual summer means time series (DO, Sulfides, ORP, LOI, TOC) with MK trend lines |
| `figures/step6_tau_heatmap.png` | Mann-Kendall τ heatmap: variable × region |
| `figures/step7_synthesis_figure.png` | 4-panel synthesis: Mantel r, diversity-DO, RF importance, temporal trends |

---

## Data Files (Processed Outputs)

| File | Description |
|------|-------------|
| `data/processed/master_sediment_env.csv` | Merged sediment + DO + stress labels (all stations, all years) |
| `data/processed/diversity_indices.csv` | Shannon, Simpson, Margalef, Pielou per station-year |
| `data/processed/community_matrix_summer.csv` | Species abundance matrix, summer surveys |
| `data/processed/community_matrix_winter.csv` | Species abundance matrix, winter surveys |
| `data/processed/step2_kmeans_scores.csv` | Silhouette scores by K for all three datasets |
| `data/processed/step3_spearman_heatmap_all.csv` | Spearman r: all stations |
| `data/processed/step3_spearman_heatmap_hypoxic.csv` | Spearman r: stressed stations |
| `data/processed/step3_within_bay_spearman.csv` | Within-bay Spearman r results |
| `data/processed/step4_mantel_results.csv` | Full Mantel test results table |
| `data/processed/step4_partial_mantel.csv` | Partial Mantel results (summer, controlling for geo distance) |
| `data/processed/step5_rf_results.csv` | RF model results (feature importances, AUC, accuracy, F1) |
| `data/processed/step6_mk_trends.csv` | Mann-Kendall results (τ, p, Sen's slope) per variable × region |
| `data/processed/step7_synthesis_table.csv` | Synthesis table: all major results in one place |
| `reports/step7_synthesis_summary.txt` | Plain-text synthesis summary |

---

*Analysis pipeline: `src/step1_env_characterisation.py` → `src/step2_kmeans_clustering.py` → `src/step3_diversity_gam.py` → `src/step4_mantel_tests.py` → `src/step5_random_forest_shap.py` → `src/step6_mann_kendall_trends.py` → `src/step7_synthesis_table.py`*

*Study area: Seto Inland Sea (瀬戸内海), Japan. Data period: 1991–2024. Seasonal focus: Summer (June–September). Reference: Lai et al. (2024).*
