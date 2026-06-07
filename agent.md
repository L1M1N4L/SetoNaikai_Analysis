# Dissolved Oxygen as the Primary Driver of Benthic Community Assembly Under Seasonal Hypoxia in the Semi-Enclosed Seto Inland Sea Japan

## Mega Prompt — Full Analysis Pipeline

---

## What This Study Is

This study reproduces and extends the analysis framework from:

> Lai, H. et al. (2024). Characteristics of demersal fish community structure during summer hypoxia in the Pearl River Estuary, China. Ecology and Evolution, 14(7), e11722. https://doi.org/10.1002/ece3.11722

The original paper examined how summer hypoxia (dissolved oxygen ≤ 2 mg/L) affects demersal fish communities in the Pearl River Estuary, China, using a single July 2021 survey across 24 stations. It used NMDS, PERMANOVA, GAMs, Mantel tests, and species/functional diversity indices to show that dissolved oxygen is the primary structuring force for fish communities under hypoxic conditions.

This study applies the same analytical logic to the Seto Inland Sea (Setonaikai), Japan — one of the world's most documented seasonal hypoxia systems — using real long-term monitoring data spanning over three decades (1991–2024). The key upgrades over the original paper are: (1) benthos instead of fish, which show stronger and more direct DO-community relationships because they cannot escape hypoxia, (2) multi-decadal temporal depth instead of a single snapshot, and (3) a hybrid unsupervised-supervised machine learning pipeline replacing pure ordination methods.

---

## Your Datasets

You have the following files. Read each one carefully before beginning any analysis step.

### fixed_line_survey_long_hiroshima.csv
Monthly shallow-sea fixed-line survey data from Hiroshima Prefecture covering Hiroshima Bay, Aki Nada, and Northern Bingo Nada for the year 2014. Shape is 1,199 rows and 6 columns: Month (1 to 12), Station (18 stations with IDs 1, 2, 4, 6, 7, 13, 15, 17, 18, 19, 20, 21, 24, 33, 34, 35, 36, 37, 38), Depth (0m, 2m, 5m, 10m, 20m, 30m, Bottom), DO in mg/L, Salinity in PSU, Temperature in degrees Celsius. This is your primary hypoxia dataset. The DO column is only available here, not in the Osaka data. Filter to Depth == Bottom for all bottom-layer analyses. Hypoxia threshold is DO ≤ 2 mg/L. Summer season is months 6 through 9.

### fixed_line_survey_long_osaka.csv
Monthly fixed-line survey from Osaka Bay for 2016 (Heisei 28). Shape is 1,143 rows and 5 columns: Month, Station (1 to 20), Depth (0m, 5m, 10m, 20m, 30m, Bottom), Salinity in PSU, Temperature in degrees Celsius. There is no DO column. Use the surface-to-bottom temperature difference as a stratification index — a difference greater than 3 degrees Celsius indicates a strong thermocline that suppresses vertical oxygen mixing and is a reliable proxy for hypoxia risk.

### fixed_station_observations_osaka.csv
Daily meteorological and oceanographic observations from the Osaka Fisheries Technology Center fixed station at Misaki town for 2016. Shape is 414 rows and 16 columns including air temperature, humidity, barometric pressure, rainfall, solar radiation, wind speed, wind direction, water temperature, and salinity. Use this as atmospheric forcing context. Rainfall drives freshwater stratification and wind speed drives stratification breakdown and hypoxia dissipation events.

### station_meta.csv
Spatial metadata for the 20 Osaka fixed-line stations. Columns are Station_ID, Latitude_N in degrees-minutes format, Longitude_E in degrees-minutes format, and Nominal_Depth_m ranging from 12 to 60 meters. Parse coordinates by splitting on the space and computing decimal degrees as degrees plus minutes divided by 60. Deeper stations are more prone to bottom hypoxia.

### bottom_2023.xlsx — sheet named 底質_累積2023
Long-term bottom sediment survey data from 1991 to 2024 across multiple sea areas of the Seto Inland Sea. Shape is 1,852 rows and 51 columns. The key columns you need are: 年 (Year), 月 (Month), 緯度_度 plus 緯度_分 plus 緯度_秒 for latitude, 経度_度 plus 経度_分 plus 経度_秒 for longitude, 水深 (water depth in meters), pH, ORP (redox potential in mV — negative values indicate reducing/anoxic conditions), 強熱減量 (loss on ignition as percentage, represents sediment organic content), COD (chemical oxygen demand in mg/g), TN (total nitrogen in mg/g), TP (total phosphorus in mg/g), TOC (total organic carbon in mg/g), 硫化物 (sulfides in mg/g — high values indicate anaerobic decomposition underway), 砂分/粘土分/礫分 (sand/clay/gravel percentages), 季節 where 2.夏 means Summer and 4.冬 means Winter, and 海域 for sea area code. Sea area codes relevant to this study are 301 through 304 for Osaka Bay and Harima Nada, and 400 for Hiroshima Bay area. This is your multi-decadal sediment oxygen demand dataset and the foundation for the Random Forest prediction model. Sampled twice yearly in summer (month 7 or 8) and winter (month 1 or 2). To convert coordinates from degrees-minutes-seconds to decimal degrees use: decimal = degrees + minutes/60 + seconds/3600.

### benthos data (from benthos_manual.xls and the broader national survey)
Benthic macrofauna species composition and abundance data from the Seto Inland Sea. This is your community matrix — the equivalent of the fish catch data in the original paper. Benthic organisms are sessile and cannot escape hypoxia the way fish can, so their community composition directly reflects accumulated oxygen stress and the DO-diversity relationships will be cleaner and stronger than those reported for fish in the original paper. The dominant stress-indicator taxa in hypoxic SIS sediments are opportunistic polychaetes such as Capitella and Mediomastus. Diverse communities with bivalves and echinoderms indicate normoxic recovery conditions.

### Environmental data folders (YYYY_SIS_wq-raw, YYYY_Osaka_wq-raw etc.)
Year-by-year raw water quality files from 1978 to 2023 covering the whole Seto Inland Sea. Each folder likely contains seasonal water quality profiles with DO at depth, temperature, salinity, and nutrients measured at fixed stations. These are the richest source for building the full multi-decadal DO time series used as the target variable in the Random Forest model. When reading these files, standardize column names to: Station, Year, Month, Depth, DO_mgL, Temp_C, Salinity_PSU. Filter to bottom-layer observations only.

---

## Why These ML Methods and Not LSTM

The original pipeline proposed using an LSTM (recurrent neural network) for temporal DO prediction. After reviewing the data structure this was rejected for three reasons. First, the sediment dataset does not sample the same fixed stations every year — sampling locations shift, so there is no consistent entity tracked through time and any sequence the LSTM would learn would be noise rather than signal. Second, with only two time points per year (summer and winter) across 33 years, the effective training set after splitting is around 40 sequences, which is far too small for LSTM to learn without severe overfitting. Third, the sediment data has no direct DO measurement, only proxy variables, adding an extra layer of assumed spatial correspondence that would compound errors in a deep learning model.

The replacement pipeline uses K-means clustering followed by Random Forest. This choice is well-supported by recent peer-reviewed literature. Millot et al. (2025) used K-means clustering combined with Random Forest modelling to group Mediterranean soft-bottom sites by biotic composition and predict their distribution from environmental variables, reporting strong predictive performance. Frontiers in Marine Science (2025) published a hybrid unsupervised-supervised pipeline using clustering for community state identification followed by supervised classification, finding that DO, depth, ORP, and sediment organic content were the most important structuring features. Random Forest has been shown to achieve 89 to 94 percent accuracy in hypoxia classification in coastal lagoons (ScienceDirect 2021, 2024) and outperforms LSTM on small ecological datasets because it requires no sequence structure, handles missing data natively, and provides interpretable feature importance through SHAP values. For the Seto Inland Sea specifically, Random Forest has already been validated for predicting water quality variables from commonly measured parameters in a 2025 Journal of Oceanography study on pCO2 estimation using SIS Comprehensive Water Quality Survey data — the same data infrastructure you are using.

---

## Analysis Pipeline

### Step 1 — Environmental Characterization and Hypoxia Zone Identification

This step reproduces Figure 3 and Figure 2 of the original paper.

Using fixed_line_survey_long_hiroshima.csv, filter to Depth == Bottom rows. For each station and month compute bottom DO, bottom temperature, and bottom salinity. Then compute the surface-to-bottom temperature difference per station-month by subtracting the bottom temperature from the 0m temperature row for the same station and month. This is your stratification index. A value greater than 3 degrees Celsius indicates a strong thermocline.

Classify each station-month as one of four oxygen regimes: normoxic (DO > 4 mg/L), moderate stress (2 < DO ≤ 4 mg/L), hypoxic (DO ≤ 2 mg/L), severely hypoxic (DO ≤ 1 mg/L). Flag any station-month with DO ≤ 2 in any summer month (6 to 9) as a hypoxic site for downstream analysis.

Compute Spearman correlations between bottom DO and each of: bottom temperature, bottom salinity, station nominal depth from station_meta.csv, and the stratification index. Report correlation coefficients and p-values in a matrix equivalent to Figure 2 of the original paper. Expected direction: bottom DO negatively correlated with depth (deeper = less mixing = lower DO) and negatively correlated with stratification index (stronger thermocline = worse hypoxia).

For Osaka, compute stratification index from fixed_line_survey_long_osaka.csv using surface-minus-bottom temperature difference. Correlate with station depth to confirm that deeper stations have stronger stratification, consistent with hypoxia risk.

---

### Step 2 — K-Means Clustering for Site Regime Classification

This step replaces the NMDS ordination and PERMANOVA from the original paper with a validated unsupervised machine learning approach that produces actionable cluster labels rather than just a visualization.

Build the feature matrix with one row per station-month observation. Features are: bottom DO, bottom temperature, bottom salinity, station nominal depth, stratification index (surface minus bottom temperature), month encoded cyclically as sine and cosine of month times 2π divided by 12 so that January and December are adjacent in feature space, and optionally sediment TOC and sulfides from bottom_2023.xlsx matched to the nearest station by decimal-degree coordinates and season.

Standardize all features to zero mean and unit variance before clustering. K-means is distance-based and sensitive to scale differences between variables.

Run K-means for K equal to 2 through 6. For each K compute the within-cluster sum of squares for the elbow plot and the silhouette score. Select the K with the highest average silhouette score. Expect K = 2 or K = 3 to be optimal, corresponding to hypoxic versus normoxic or hypoxic versus transitional versus normoxic regimes.

Validate by cross-tabulating cluster assignments against the hypoxia flag (DO ≤ 2 yes or no). A good clustering should recover the hypoxia threshold with high agreement. Report cluster centroids in the original unstandardized feature space so they are ecologically interpretable, for example Cluster A has mean DO of 1.4 mg/L, mean depth of 45 m, mean stratification index of 5.2 degrees Celsius.

This is the equivalent of the original paper's PERMANOVA result which found R² = 0.10, p = 0.003 showing significant community separation between hypoxic and normoxic zones.

---

### Step 3 — Benthic Diversity Indices and GAM Analysis

This step reproduces Table S3 and Figures 6 and 7 of the original paper.

Build a species-by-station abundance matrix from the benthic macrofauna dataset. Compute the following diversity indices per station per season: Shannon index H prime equals negative sum of pi times log of pi where pi is the relative abundance of species i, Simpson index as 1 minus sum of pi squared, Margalef richness as S minus 1 divided by the natural log of N where S is species count and N is total individuals, and Pielou evenness as H prime divided by the natural log of S.

Join each station-season diversity value with the corresponding bottom DO value from the Hiroshima fixed-line data or the multi-year SIS environmental data, matching by station identifier, year, and season.

Run Generalized Additive Models with each diversity index as the response and bottom DO as the smooth predictor term using a cubic spline with 3 to 5 degrees of freedom. Run the GAMs twice: once for all stations and once for hypoxic stations only (bottom DO ≤ 2 mg/L in that season). This directly replicates Figure 6.

Also compute Spearman correlations between each diversity index and each environmental variable (DO, temperature, salinity, depth, stratification index, sediment TOC if available). Present as a heatmap with significance stars, equivalent to Figure 7. Run separately for all stations and for hypoxic stations only.

Expected results consistent with the original paper: within hypoxic stations, Shannon, Simpson, and Margalef all show significant positive correlation with DO (original paper found r = 0.77, 0.73, and 0.67 respectively). Functional divergence index FDiv is expected to decrease with increasing DO in the hypoxic zone, indicating that low-DO conditions select for functionally divergent stress specialists while higher DO allows generalist return and trait homogenization.

---

### Step 4 — Mantel Test for Community-Environment Correlation

This step reproduces Figure 9 of the original paper.

Compute a Bray-Curtis dissimilarity matrix between all pairs of stations based on benthic species relative abundances. Compute Euclidean distance matrices for each environmental variable separately: DO, temperature, salinity, depth, and stratification index.

Run Spearman-based Mantel tests between the community dissimilarity matrix and each environmental distance matrix using 999 permutations. Run for all stations and for hypoxic stations only.

Report Mantel r and p-value for each variable in both subsets. Expected result mirroring the original paper: DO has a significantly stronger Mantel r inside the hypoxic zone than across all stations, confirming that DO is the primary structuring force under hypoxic conditions while depth, temperature, and salinity act as secondary filters. The original paper found Mantel r = 0.36, p = 0.011 for DO in the hypoxic zone.

---

### Step 5 — Random Forest for Hypoxia Prediction and Driver Identification

This step is the novel machine learning contribution that extends beyond the original paper's scope and is justified by the published literature on RF-based hypoxia prediction in coastal systems.

The scientific question is: given the sediment condition (organic load, redox state, sulfide accumulation) and basic environmental context (depth, season, year), can you predict whether a location will experience hypoxic conditions? This operationalizes the paper's causal narrative — that benthic oxygen demand from sediment decomposition drives bottom DO depletion — into a predictive model.

Build the feature matrix from bottom_2023.xlsx using summer observations. Features per observation are: TOC, sulfides, ORP, COD, loss on ignition (強熱減量), clay fraction (粘土分), water depth (水深), month, year, and sea area code. Target variable is binary: hypoxic (summer DO ≤ 2 mg/L at that location) or normoxic. Where direct DO measurements are available from the SIS environmental folders for matching station coordinates and year, use those as ground truth labels. Where DO is not directly available, use ORP less than negative 100 mV AND sulfides greater than 0.2 mg/g AND LOI greater than 5 percent as a composite hypoxia-risk label, which is ecologically validated for anoxic sediment conditions.

Split data into training (1991 to 2010), validation (2011 to 2017), and test (2018 to 2024) sets. This temporal split is important — do not use random splitting because it would allow future sediment conditions to inform past predictions, leaking information across time.

Train a Random Forest classifier with 200 to 500 trees, max depth of 10 to 15, and minimum samples per leaf of 5 to prevent overfitting on the small dataset. Tune hyperparameters using the validation set. Evaluate on the test set using accuracy, AUC-ROC, F1 score, and confusion matrix. Based on published results from similar coastal systems, expect accuracy of 85 to 94 percent.

Compute SHAP (SHapley Additive exPlanations) values for each feature to produce an interpretable feature importance ranking. Expected top predictors consistent with the literature and with the original paper's narrative: TOC and sulfides will be the strongest predictors because they represent accumulated organic oxygen demand, followed by ORP (redox state), water depth (stratification susceptibility), and year (long-term eutrophication trend).

Plot SHAP summary plot showing mean absolute SHAP value per feature. Plot SHAP dependence plots for TOC versus hypoxia probability and sulfides versus hypoxia probability to show the nonlinear threshold relationships.

Also run Random Forest as a regressor predicting continuous summer bottom DO rather than binary hypoxia class. Report RMSE and R² on the test set.

---

### Step 6 — Long-Term Trend Analysis

This step uses your unique multi-decadal data advantage — something the original paper, based on a single survey, could not do.

Using the bottom_2023.xlsx sediment data from 1991 to 2024, run Mann-Kendall trend tests on the following annual summer means per sea area: TOC, sulfides, ORP, COD, and loss on ignition. Mann-Kendall is a non-parametric monotonic trend test that is standard in long-term fisheries and environmental monitoring studies in Japan and directly comparable to what SIS management agencies report.

The Seto Inland Sea has been subject to nutrient load regulations since the 1970s and strengthened again in the 2000s. Expect a long-term improvement signal (declining TOC, improving ORP, lower sulfides) in regulated sea areas like Osaka Bay, and potentially a stagnation or worsening trend in less regulated outer areas. Report Sen's slope (the rate of change per year) alongside the Mann-Kendall tau and p-value.

Cross-reference these sediment trends with the Random Forest feature importance output. If TOC is the top predictor of hypoxia and TOC shows a significant declining trend since 2000, this provides a mechanistic explanation for any observed recovery of benthic communities in the same period — directly connecting your ML model outputs to the ecological narrative.

---

### Step 7 — Synthesis Table

After completing all steps produce the following comparison table between your study and the original paper:

| Analysis element | Original paper Pearl River Estuary | This study Seto Inland Sea |
|---|---|---|
| Study system | Subtropical Chinese estuary | Semi-enclosed Japanese inland sea |
| Survey type | Single July 2021 trawl survey | Multi-decadal fixed-line monitoring 1991 to 2024 |
| Community studied | Demersal fish 104 species | Benthic macrofauna report your species count |
| Hypoxia prevalence | 11 of 24 sites hypoxic | Report your result |
| Primary DO driver | Thermal stratification | Thermal stratification plus sediment oxygen demand |
| Shannon versus DO all sites | No significant correlation | Report your result |
| Shannon versus DO hypoxic only | r = 0.77 p = 0.006 | Report your result |
| FDiv versus DO direction | Negative decreases with DO | Report your result |
| Mantel DO hypoxic only | r = 0.36 p = 0.011 | Report your result |
| Temporal trend capability | None single snapshot | Mann-Kendall 33 years |
| ML method | None traditional statistics only | K-means clustering plus Random Forest with SHAP |
| Hypoxia prediction accuracy | Not applicable | Report AUC and F1 |

Discuss differences in terms of ecosystem type, taxonomic group, data resolution, and geographic scale. Emphasize that using benthos instead of fish strengthens the DO-community relationship because benthos cannot migrate away from hypoxic zones, making them more reliable indicators of chronic oxygen stress.

---

## Key Thresholds and Definitions

Use these consistently throughout the paper:

Normoxic: DO greater than 4 mg/L. Moderate stress: DO between 2 and 4 mg/L. Hypoxic: DO at or below 2 mg/L. Severely hypoxic: DO at or below 1 mg/L. Near-anoxic: DO at or below 0.5 mg/L.

Summer hypoxia season in the Seto Inland Sea: June through September (months 6 to 9). Peak hypoxia typically in August. Hypoxia begins in May and dissipates in autumn with cooling and storm-driven mixing.

Hypoxic sediment indicators: ORP below negative 100 mV, sulfides above 0.2 mg/g, loss on ignition above 5 percent, COD above 10 mg/g.

---

## Literature the AI Should Be Aware Of

Lai et al. 2024 Ecology and Evolution is the direct template paper. The full citation is in the header of this document.

Millot et al. 2025 used K-means clustering combined with Random Forest to partition Mediterranean soft-bottom sites into megabenthic community types from environmental variables — this is the closest methodological precedent for Steps 2 and 5.

Frontiers in Marine Science 2025 published a hybrid unsupervised-supervised ML pipeline for marine ecological communities finding DO, depth, ORP, and sediment organic content as top structuring features — validates the feature set used in Step 5.

ScienceDirect 2021 and 2024 published Random Forest hypoxia classification in coastal lagoons achieving 89 to 94 percent accuracy — sets the expected performance benchmark for Step 5.

Journal of Oceanography 2025 validated Random Forest for water quality estimation specifically in the Seto Inland Sea using the Comprehensive Water Quality Survey data — the same data infrastructure used in this study.

Breitburg et al. 2018 Science provides global context on coastal hypoxia expansion since 1950 — cite in the introduction.

Vaquer-Sunyer and Duarte 2008 established that fish are among the most sensitive marine organisms to hypoxia — explains why the original paper focused on fish and why benthos are an equally valid and arguably stronger signal.

---

## Expected Final Outputs

Map of bottom DO distribution across Hiroshima Bay stations by month with hypoxic zones highlighted.

Spearman correlation matrix of bottom environmental variables equivalent to Figure 2 of the original paper.

Elbow plot and silhouette score plot for K-means cluster selection, followed by a scatter plot of cluster assignments in DO-temperature-depth space.

Cross-tabulation table of K-means clusters versus hypoxia flag showing classification agreement.

GAM plots of Shannon, Simpson, Margalef, Pielou, and FDiv versus bottom DO for all stations and hypoxic stations separately equivalent to Figure 6.

Heatmap of Spearman correlations between diversity indices and environmental variables for all stations and hypoxic stations separately equivalent to Figure 7.

Mantel test results table equivalent to Figure 9.

Random Forest confusion matrix, AUC-ROC curve, and SHAP summary plot.

Mann-Kendall trend plots for TOC, sulfides, and ORP per sea area from 1991 to 2024.

Synthesis comparison table between this study and the original PRE paper.

---

## Data Audit and Preprocessing Pipeline

This section documents every raw data source as it actually exists on disk, what is wrong or irregular with each, and the exact cleaning steps required before any analysis step can begin. Run this pipeline in order before touching any analysis step. All outputs go to data/processed/ and data/processed/seasonal/ as appropriate.

---

### True Raw Data Inventory

The raw data is in four locations. Nothing is empty.

**data/raw/benthos_data/**
- benthos_2023.xlsx — sheet name 底生生物_累積2023 — benthic macrofauna community matrix in wide format. Header row is row index 1 (the second row). Row 0 is a Japanese note about stations with more than 62 species. Each data row is one station-survey event. Columns after the five metadata columns (年度, 県コード, 連番, 県番号, 調査年月日) contain species data as repeating groups of four columns each: 学名N (Latin name), 和名N (Japanese name), 個体数N (individual count), 湿重量N (wet weight in grams). There are up to 63 such groups per row, giving 5 + 63×4 = 257 columns. Species 63 and beyond overflow to the next row, which is flagged by cell colour in the original Excel but invisible in a programmatic read.
- bottom_2023.xlsx — sheet name 底質_累積2023 — sediment geochemistry. 1852 rows, 50 columns. Each measurement variable appears twice: once as a raw string column (e.g. C_COD) which may contain non-numeric quality flags, and once as a parsed float column (e.g. COD) which is NaN when the string was non-numeric. Always use the float column for calculations.

**data/raw/environmental_data/**
Contains 181 subdirectories named YYYY_REGION_wq-raw where REGION is SIS, Osaka, Ise, or Tokyo. Each subdirectory is a shapefile set (output.shp, .dbf, .prj, .shx, plus sidecar files). The DBF schema is identical across all years and regions. There are 900 records per file on average. The key numeric columns are: do_2 (dissolved oxygen mg/L float), salt2 (salinity PSU float), wtemp (water temperature degrees Celsius string — some entries are strings with flags), ph2 (pH float), toc2 (total organic carbon mg/L float), tn2 (total nitrogen mg/L float), tp2 (total phosphorus mg/L float), cod2 (COD mg/L float), nh4n2, no2n2, no3n2 (nutrient fractions mg/L float), chloroph_1 (chlorophyll-a mg/L float). Spatial columns are latitude and longitude in decimal degrees (already converted). Station identity is captured by zettaicode (8-character fixed-point station code), uniqueid, watercode, and wancode. Depth information is in saisuipoin (sampling point code, where 1 = surface and higher numbers = deeper) and the string field depth. Year and month are in surveyyear and surveymont.

**data/raw/environmental_manual/**
Three files: benthos_manual.xls, bottom_manual.xls, water_manual.xls. These are small supplementary datasets from manual surveys used to cross-validate the main datasets. Read them with header=0 and inspect column names before use.

**data/raw/Fixed_line_survey/**
Four CSV files that are already clean and described in the Your Datasets section above. No further cleaning is needed beyond coordinate parsing for station_meta.csv.

**data/raw/JODC_mesh500_SIS/**
Eleven text files of the JODC 500m bathymetric mesh grid covering the Seto Inland Sea. These are grid files with columns: mesh code, latitude, longitude, depth in meters. Use for spatial depth assignment when station depth is missing.

---

### What to Clean in Each Dataset

#### Environmental Shapefiles — Critical Issues

Issue 1: Duplicate columns. Every measurement appears as both a raw string column (do_, salt, cod, tn, tp, toc, nh4n, no2n, no3n, po4p, chlorophyl, feiochin, doc) and a parsed float column (do_2, salt2, cod2, tn2, tp2, toc2, nh4n2, no2n2, no3n2, po4p2, chloroph_1, feiochin2, doc2). Drop all raw string columns and keep only the float columns.

Issue 2: Depth ambiguity. The field saisuipoin encodes sampling depth by index, not by actual meters. The field depth is a string that may say the actual depth in meters or a label like surface or bottom. You must map saisuipoin values to actual depth categories: find all unique saisuipoin values in the data and check the corresponding depth strings to build a lookup table. For this study you want only bottom-layer observations. Surface is typically saisuipoin == 1. Bottom is typically the highest saisuipoin value at each station for that survey date. Select bottom observations by filtering to the maximum saisuipoin value per (zettaicode, survey_ym) group.

Issue 3: wtemp is a string column. Convert to float and coerce non-numeric values to NaN.

Issue 4: Out-of-range values. After conversion, apply these physical bounds and set out-of-range values to NaN. DO must be between 0 and 20 mg/L. Salinity must be between 0 and 40 PSU. Temperature must be between 0 and 35 degrees Celsius. pH must be between 6.5 and 9.5. COD must be between 0 and 30 mg/L. Negative DO values exist in the raw data for near-anoxic sites measured with imprecise instruments — clamp these to 0 rather than dropping them entirely, then flag with a boolean is_near_anoxic column.

Issue 5: Year coverage gaps. Not all years have SIS-wide files. Ise Bay and Tokyo Bay data start in 1978 while SIS-wide and Osaka files start in 1981. Some years before 1985 have very low record counts. Check record counts by year before including early data in trend analyses.

Issue 6: Spatial duplicates. Some zettaicodes have multiple records in the same survey month due to revisits or corrected entries. Keep the record with the lowest dataflag value (0 = good, higher = suspect). Where dataflag is equal, keep the record with the higher scale value (1 = measured, lower = estimated).

#### bottom_2023.xlsx — Critical Issues

Issue 1: Quality flag columns. The C_ prefix columns (C_COD, C_ORP, C_強熱減量, etc.) contain non-numeric quality codes such as less-than signs (< 0.01), estimated flags, or blank codes indicating censored or estimated values. Where a C_ column contains a less-than sign, the true value is below the detection limit. Set the corresponding float column to half the detection limit value rather than NaN, and add a boolean is_censored_VARNAME column. Where the C_ column contains an estimated flag, retain the float value but add a boolean is_estimated_VARNAME column.

Issue 2: Coordinate conversion. Coordinates are stored as degrees-minutes-seconds in three separate integer columns each for latitude (緯度_度, 緯度_分, 緯度_秒) and longitude (経度_度, 経度_分, 経度_秒). Convert to decimal degrees: lat_dd = 緯度_度 + 緯度_分/60 + 緯度_秒/3600 and similarly for longitude.

Issue 3: Season encoding. The 季節 column contains values like 2.夏 and 4.冬. Parse the leading digit: 2 = Summer, 4 = Winter. Create a clean Season column with values Summer and Winter.

Issue 4: Sea area codes. The 海域 column is the primary spatial filter for this study. Sea area codes 301 to 304 cover Osaka Bay and Harima Nada. Code 400 covers Hiroshima Bay. Other codes may represent outer areas or comparison regions. Keep all codes but use 301 to 304 and 400 as the primary study area subset for the Random Forest model.

Issue 5: Annual means. When computing annual summer means per sea area for Mann-Kendall trend analysis, some year-area combinations have fewer than 3 observations due to sampling gaps. Flag these with a low_n boolean and exclude from trend plots but include in raw data tables.

#### benthos_2023.xlsx — Critical Issues

Issue 1: Wide to long transformation. The file is in wide format with one row per station-survey and species data spread across 63 groups of four columns. The correct parsing procedure is: read with header=1 to pick up the correct column names, select the five metadata columns, then iterate over groups of four columns starting at column index 5, each group being (学名N, 和名N, 個体数N, 湿重量N). For each group where 個体数N is not NaN and not zero, emit one row to the long-format output with columns: 年度, 県コード, 連番, 県番号, 調査年月日, 学名 (Latin name), 和名 (Japanese name), 個体数 (count), 湿重量 (wet weight g). This will produce a long-format species-station-date abundance table.

Issue 2: Overflow rows. When a station has more than 62 species, the additional species are recorded in the following row with the same metadata columns. Detect overflow rows by checking whether 年度 in the current row equals 年度 in the previous row AND 連番 equals the previous 連番. Merge overflow species into the same station record before pivoting.

Issue 3: Species name standardisation. Latin names may contain typos, abbreviated authorities, or trailing whitespace. Apply str.strip() to all Latin name entries and build a species lookup table of unique names after cleaning. Species appearing fewer than 3 times across all stations should be grouped as Rare_sp for diversity calculations but kept individually for community matrix analysis.

Issue 4: Temporal join preparation. The survey date is in 調査年月日 as a datetime. Extract Year and Month. The sampling is twice yearly in summer (July or August) and winter (January or February). Create a Season column matching the bottom sediment convention: months 7 and 8 = Summer, months 1 and 2 = Winter. This is the join key to the bottom_2023 and environmental shapefile datasets.

---

### Preprocessing Pipeline — Step by Step

Run the following scripts in order. Each script reads from raw and writes to processed. Do not modify raw files.

#### Script 1: preprocess_environmental.py

Purpose: Merge all YYYY_REGION_wq-raw shapefiles into a single clean bottom-layer water quality time series.

```
import os, glob, struct
import pandas as pd
import numpy as np

RAW_ENV = "data/raw/environmental_data"
OUT = "data/processed/env_bottom_timeseries.csv"

FLOAT_COLS = ['do_2','salt2','ph2','toc2','tn2','tp2','cod2',
              'nh4n2','no2n2','no3n2','po4p2','chloroph_1','feiochin2','doc2']
META_COLS  = ['uniqueid','zettaicode','locationna','wancode','prefectuei',
              'watercode','renban','nendo','survey_ym','surveyyear',
              'surveymont','surveyday','surveyhour','surveymini',
              'saisuipoin','latitude','longitude','dataflag','scale']

frames = []
for dbf_path in glob.glob(os.path.join(RAW_ENV, "*_wq-raw", "output.dbf")):
    region = os.path.basename(os.path.dirname(dbf_path)).split('_')[1]
    year   = int(os.path.basename(os.path.dirname(dbf_path)).split('_')[0])
    # Read DBF without geopandas using pyshp or manual struct
    # Use: pip install pyshp then import shapefile
    import shapefile
    sf = shapefile.Reader(dbf_path.replace('.dbf',''))
    fields = [f[0] for f in sf.fields[1:]]
    records = sf.records()
    df = pd.DataFrame(records, columns=fields)
    df['region'] = region
    df['year_folder'] = year
    frames.append(df)

df_all = pd.concat(frames, ignore_index=True)

# Clean wtemp
df_all['wtemp'] = pd.to_numeric(df_all['wtemp'], errors='coerce')

# Physical bounds
bounds = {'do_2':(0,20),'salt2':(0,40),'wtemp':(0,35),
          'ph2':(6.5,9.5),'cod2':(0,30)}
for col,(lo,hi) in bounds.items():
    if col in df_all.columns:
        df_all.loc[df_all[col] < lo, col] = np.nan
        df_all.loc[df_all[col] > hi, col] = np.nan

# Clamp negative DO to 0 and flag
df_all['is_near_anoxic'] = df_all['do_2'] <= 0
df_all['do_2'] = df_all['do_2'].clip(lower=0)

# Select bottom layer: max saisuipoin per station-survey
df_all['saisuipoin'] = pd.to_numeric(df_all['saisuipoin'], errors='coerce')
df_all['dataflag']   = pd.to_numeric(df_all['dataflag'], errors='coerce').fillna(9)
df_all['scale']      = pd.to_numeric(df_all['scale'], errors='coerce').fillna(0)

# Sort so best quality comes first, then take last saisuipoin per group
df_all = df_all.sort_values(['dataflag','scale'], ascending=[True,False])
bottom = (df_all.groupby(['zettaicode','survey_ym'], as_index=False)
                .apply(lambda g: g.loc[g['saisuipoin'].idxmax()])
                .reset_index(drop=True))

bottom[META_COLS + ['wtemp','region','is_near_anoxic'] + FLOAT_COLS].to_csv(OUT, index=False)
print(f"Saved {len(bottom)} bottom-layer records to {OUT}")
```

Output file: data/processed/env_bottom_timeseries.csv
Columns in output: uniqueid, zettaicode, locationna, wancode, watercode, survey_ym, surveyyear, surveymont, latitude, longitude, saisuipoin, dataflag, scale, region, wtemp, is_near_anoxic, do_2, salt2, ph2, toc2, tn2, tp2, cod2, nh4n2, no2n2, no3n2, po4p2, chloroph_1.

This file is the master environmental dataset and the source of the target variable (do_2) for the Random Forest model and the yearly_do_df pivots in processed/seasonal/.

#### Script 2: preprocess_bottom_sediment.py

Purpose: Parse bottom_2023.xlsx, handle censored values, convert coordinates, clean season and sea area labels.

```
import pandas as pd
import numpy as np

df = pd.read_excel("data/raw/benthos_data/bottom_2023.xlsx",
                   sheet_name="底質_累積2023", header=0)

# Coordinate conversion
df['lat_dd'] = df['緯度_度'] + df['緯度_分']/60 + df['緯度_秒']/3600
df['lon_dd'] = df['経度_度'] + df['経度_分']/60 + df['経度_秒']/3600

# Season
df['Season'] = df['季節'].astype(str).str[0].map({'2':'Summer','4':'Winter'})

# Sea area: clean to integer
df['sea_area'] = pd.to_numeric(df['海域コード'], errors='coerce')

# For each measurement: handle C_ flag columns
meas_cols = ['礫分','砂分','粘土分','pH','ORP','乾燥減量',
             '強熱減量','COD','TN','TP','TOC','硫化物']
for col in meas_cols:
    flag_col = f'C_{col}'
    if flag_col not in df.columns:
        continue
    flag_str = df[flag_col].astype(str)
    # Detect less-than (censored)
    is_censored = flag_str.str.contains('<', na=False)
    df[f'is_censored_{col}'] = is_censored
    # Where censored, set value to half detection limit (value already parsed as float)
    df.loc[is_censored, col] = df.loc[is_censored, col] / 2
    # Estimated flag (non-blank, non-< string in C_ col)
    is_estimated = (~is_censored) & (flag_str.notna()) & (flag_str != 'nan') & (flag_str != '')
    df[f'is_estimated_{col}'] = is_estimated

# Physical sanity bounds for sediment
df.loc[df['TOC'] < 0, 'TOC'] = np.nan
df.loc[df['硫化物'] < 0, '硫化物'] = np.nan
df.loc[df['ORP'] > 300, 'ORP'] = np.nan   # ORP above +300 mV is implausible in bottom sediment
df.loc[df['ORP'] < -400, 'ORP'] = np.nan

keep = ['年','月','Season','lat_dd','lon_dd','水深','sea_area',
        'pH','ORP','乾燥減量','強熱減量','COD','TN','TP','TOC','硫化物',
        '礫分','砂分','粘土分'] + \
       [c for c in df.columns if c.startswith('is_censored_') or c.startswith('is_estimated_')]

df[keep].to_csv("data/processed/bottom_sediment_clean.csv", index=False, encoding='utf-8-sig')
print(f"Saved {len(df)} sediment records")
```

Output file: data/processed/bottom_sediment_clean.csv

#### Script 3: preprocess_benthos.py

Purpose: Parse benthos_2023.xlsx wide format to long format species-station abundance table.

```
import pandas as pd
import numpy as np

df = pd.read_excel("data/raw/benthos_data/benthos_2023.xlsx",
                   sheet_name="底生生物_累積2023", header=1)

META = ['年度','県コード','連番','県番号','調査年月日']
species_cols = [c for c in df.columns if c not in META]

# Detect overflow rows: same 年度 and 連番 as previous row
df['is_overflow'] = (df['年度'] == df['年度'].shift(1)) & (df['連番'] == df['連番'].shift(1))

# Melt wide to long
# Groups of 4 columns: 学名N, 和名N, 個体数N, 湿重量N
non_meta = df.columns[5:].tolist()
n_groups = len(non_meta) // 4

records = []
for _, row in df.iterrows():
    meta = {m: row[m] for m in META}
    meta['is_overflow'] = row['is_overflow']
    for i in range(n_groups):
        base = 5 + i * 4
        latin  = df.columns[base]
        jname  = df.columns[base+1]
        count  = df.columns[base+2]
        weight = df.columns[base+3]
        n = row[count]
        if pd.isna(n) or n == 0:
            continue
        records.append({**meta,
                        '学名': str(row[latin]).strip(),
                        '和名': str(row[jname]).strip(),
                        '個体数': n,
                        '湿重量_g': row[weight]})

long_df = pd.DataFrame(records)
long_df['Year']  = pd.to_datetime(long_df['調査年月日']).dt.year
long_df['Month'] = pd.to_datetime(long_df['調査年月日']).dt.month
long_df['Season'] = long_df['Month'].map(
    lambda m: 'Summer' if m in [7,8] else ('Winter' if m in [1,2] else 'Other'))

# Flag rare species
counts = long_df['学名'].value_counts()
long_df['学名_clean'] = long_df['学名'].where(
    long_df['学名'].isin(counts[counts >= 3].index), other='Rare_sp')

long_df.to_csv("data/processed/benthos_long.csv", index=False, encoding='utf-8-sig')
print(f"Saved {len(long_df)} species-station records from {long_df['連番'].nunique()} stations")
```

Output file: data/processed/benthos_long.csv
Columns: 年度, 県コード, 連番, 県番号, 調査年月日, is_overflow, 学名, 和名, 個体数, 湿重量_g, Year, Month, Season, 学名_clean

#### Script 4: build_community_matrix.py

Purpose: Pivot benthos_long.csv into a species-by-station matrix for diversity calculation and Mantel tests.

```
import pandas as pd

df = pd.read_csv("data/processed/benthos_long.csv", encoding='utf-8-sig')

# One matrix per season
for season in ['Summer','Winter']:
    sub = df[df['Season'] == season]
    # Pivot: index = station (連番) + Year, columns = 学名_clean, values = 個体数
    mat = sub.pivot_table(index=['連番','Year'], columns='学名_clean',
                          values='個体数', aggfunc='sum', fill_value=0)
    mat.to_csv(f"data/processed/community_matrix_{season.lower()}.csv", encoding='utf-8-sig')
    print(f"{season}: {mat.shape[0]} station-year rows, {mat.shape[1]} species")
```

Output files: data/processed/community_matrix_summer.csv, data/processed/community_matrix_winter.csv

#### Script 5: build_master_joined.py

Purpose: Join env_bottom_timeseries.csv + bottom_sediment_clean.csv + benthos diversity indices into one master analytical table for all modelling steps.

```
import pandas as pd
import numpy as np
from scipy.spatial import cKDTree

env = pd.read_csv("data/processed/env_bottom_timeseries.csv")
sed = pd.read_csv("data/processed/bottom_sediment_clean.csv", encoding='utf-8-sig')
ben = pd.read_csv("data/processed/benthos_long.csv", encoding='utf-8-sig')

env['Year']  = env['surveyyear'].astype(int)
env['Month'] = env['surveymont'].astype(int)
env['Season'] = env['Month'].apply(
    lambda m: 'Summer' if m in [6,7,8,9] else ('Winter' if m in [1,2,3] else 'Other'))

# Spatial join env to sediment using nearest-neighbour (haversine)
# For each sediment record find closest env station in same year-season
def haversine_matrix(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = np.radians(lat2[:,None] - lat1[None,:])
    dlon = np.radians(lon2[:,None] - lon1[None,:])
    a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2[:,None])) * np.sin(dlon/2)**2
    return 2 * R * np.arcsin(np.sqrt(a))

# Join summer sediment to summer env DO
sed_s = sed[sed['Season'] == 'Summer'].copy()
env_s = env[env['Season'].isin(['Summer'])].copy()

joined_rows = []
for year in sed_s['年'].unique():
    s_yr = sed_s[sed_s['年'] == year]
    e_yr = env_s[env_s['Year'] == year]
    if e_yr.empty:
        continue
    dist = haversine_matrix(
        e_yr['latitude'].values, e_yr['longitude'].values,
        s_yr['lat_dd'].values, s_yr['lon_dd'].values)
    idx = dist.argmin(axis=1)
    dist_min = dist.min(axis=1)
    matched_env = e_yr.iloc[idx][['do_2','salt2','wtemp','zettaicode']].values
    s_yr = s_yr.copy()
    s_yr['do_nearest'] = matched_env[:,0].astype(float)
    s_yr['salt_nearest'] = matched_env[:,1].astype(float)
    s_yr['wtemp_nearest'] = matched_env[:,2].astype(float)
    s_yr['env_zettaicode'] = matched_env[:,3]
    s_yr['env_dist_km'] = dist_min
    joined_rows.append(s_yr)

master = pd.concat(joined_rows, ignore_index=True)
# Flag suspect spatial joins (more than 20 km from nearest env station)
master['env_join_suspect'] = master['env_dist_km'] > 20

master.to_csv("data/processed/master_sediment_env.csv", index=False, encoding='utf-8-sig')
print(f"Master table: {len(master)} rows")
```

Output file: data/processed/master_sediment_env.csv

This is the input table for the Random Forest model in Step 5.

---

### What to Regenerate in data/processed/

The existing processed files were derived from the raw shapefiles. They are valid and can be kept, but you need to understand their provenance:

- yearly_do_df.csv and seasonal/*/yearly_do_df.csv: These are year × zettaicode pivot tables of mean bottom DO by season derived from the environmental shapefiles. They are generated from all SIS shapefiles. Keep them but verify they were built using bottom-layer observations only (saisuipoin filter). If uncertain, regenerate from env_bottom_timeseries.csv by pivoting on surveyyear and zettaicode.
- interpolated_do_df.csv and seasonal/*/interpolated_do_df.csv: Spatial gap-filling of yearly_do_df using kriging or IDW interpolation. These depend on the dist_matrix_km and stations_decorrelation_scale files. Keep them as-is — they represent substantial prior computation.
- pca_loadings.csv, pca_scores.csv, pca_variance.csv and the EOF variants in seasonal/summer_bottom/: These are PCA/EOF decompositions of the yearly DO matrices. Keep them — they are already valid and feed the spatial analysis background.
- merged_gdf.feather and related GIS files: These merged the shapefile attribute data with spatial geometries. Keep them for mapping purposes but do not use them as the primary analytical source — use env_bottom_timeseries.csv instead for cleaner column control.
- dist_matrix_km.csv and stations_decorrelation_scale.csv: These are spatial statistics and are independent of the cleaning steps. Keep them.

New files to add to data/processed/ that do not yet exist:
- env_bottom_timeseries.csv — from Script 1
- bottom_sediment_clean.csv — from Script 2
- benthos_long.csv — from Script 3
- community_matrix_summer.csv — from Script 4
- community_matrix_winter.csv — from Script 4
- master_sediment_env.csv — from Script 5

---

### Column Name Reference for All Steps

When any analysis step refers to DO, temperature, salinity, or other variables, use these column names from the processed files:

From env_bottom_timeseries.csv: do_2 (DO mg/L), salt2 (salinity PSU), wtemp (temperature °C), zettaicode (station ID), surveyyear (year integer), surveymont (month integer), latitude (decimal degrees N), longitude (decimal degrees E), region (SIS/Osaka/Ise/Tokyo).

From bottom_sediment_clean.csv: TOC (mg/g), 硫化物 (sulfides mg/g), ORP (mV), COD (mg/g), 強熱減量 (loss on ignition %), TN (mg/g), TP (mg/g), 粘土分 (clay %), 水深 (depth m), lat_dd, lon_dd, 年 (year), Season.

From benthos_long.csv: 連番 (station number), Year, Month, Season, 学名 (Latin species name), 学名_clean (cleaned or Rare_sp), 個体数 (count), 湿重量_g (wet weight).

From master_sediment_env.csv: all bottom_sediment_clean columns plus do_nearest (matched DO mg/L), env_dist_km (distance to nearest env station km), env_join_suspect (boolean flag for joins over 20 km).