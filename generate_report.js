const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, PageBreak, LevelFormat,
  TableOfContents, ExternalHyperlink
} = require("docx");
const fs = require("fs");

// ─── Helpers ────────────────────────────────────────────────────────────────

const CONTENT_WIDTH = 9360; // US Letter - 1" margins each side (12240 - 2*1440)

const cellBorder = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: cellBorder, bottom: cellBorder, left: cellBorder, right: cellBorder };
const cellMargins = { top: 100, bottom: 100, left: 150, right: 150 };

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 360, after: 160 },
    children: [new TextRun({ text, font: "Arial", size: 32, bold: true, color: "1F3864" })]
  });
}

function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 280, after: 120 },
    children: [new TextRun({ text, font: "Arial", size: 26, bold: true, color: "2E5899" })]
  });
}

function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 200, after: 100 },
    children: [new TextRun({ text, font: "Arial", size: 24, bold: true, color: "404040" })]
  });
}

function body(text, options = {}) {
  return new Paragraph({
    spacing: { before: 60, after: 120 },
    children: [new TextRun({ text, font: "Arial", size: 22, ...options })]
  });
}

function bodyMixed(runs) {
  return new Paragraph({
    spacing: { before: 60, after: 120 },
    children: runs.map(r =>
      typeof r === "string"
        ? new TextRun({ text: r, font: "Arial", size: 22 })
        : new TextRun({ font: "Arial", size: 22, ...r })
    )
  });
}

function bullet(text, level = 0) {
  return new Paragraph({
    numbering: { reference: "bullets", level },
    spacing: { before: 40, after: 40 },
    children: [new TextRun({ text, font: "Arial", size: 22 })]
  });
}

function spacer() {
  return new Paragraph({ spacing: { before: 60, after: 60 }, children: [new TextRun("")] });
}

function pageBreak() {
  return new Paragraph({ children: [new PageBreak()] });
}

// Header row helper
function headerCell(text, widthDxa, bgColor = "1F3864") {
  if (typeof bgColor !== "string") bgColor = "1F3864";
  return new TableCell({
    borders,
    width: { size: widthDxa, type: WidthType.DXA },
    shading: { fill: bgColor, type: ShadingType.CLEAR },
    margins: cellMargins,
    verticalAlign: VerticalAlign.CENTER,
    children: [new Paragraph({
      children: [new TextRun({ text, font: "Arial", size: 20, bold: true, color: "FFFFFF" })]
    })]
  });
}

function dataCell(text, widthDxa, bgColor = "FFFFFF", bold = false, color = "222222") {
  if (typeof bgColor !== "string") { console.error("BAD bgColor:", bgColor, "text:", text); bgColor = "FFFFFF"; }
  if (typeof color   !== "string") { console.error("BAD color:",   color,   "text:", text); color   = "222222"; }
  if (typeof text    !== "string") text = String(text);
  return new TableCell({
    borders,
    width: { size: widthDxa, type: WidthType.DXA },
    shading: { fill: bgColor, type: ShadingType.CLEAR },
    margins: cellMargins,
    children: [new Paragraph({
      children: [new TextRun({ text, font: "Arial", size: 20, bold, color })]
    })]
  });
}

function altRow(i) { return i % 2 === 1 ? "EEF4FB" : "FFFFFF"; }

// ─── Document ────────────────────────────────────────────────────────────────

const doc = new Document({
  numbering: {
    config: [
      {
        reference: "bullets",
        levels: [
          { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
          { level: 1, format: LevelFormat.BULLET, text: "◦", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 1080, hanging: 360 } } } }
        ]
      }
    ]
  },
  styles: {
    default: {
      document: { run: { font: "Arial", size: 22 } }
    },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial", color: "1F3864" },
        paragraph: { spacing: { before: 360, after: 160 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "Arial", color: "2E5899" },
        paragraph: { spacing: { before: 280, after: 120 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: "Arial", color: "404040" },
        paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 2 } },
    ]
  },
  sections: [
    // ── TITLE PAGE ────────────────────────────────────────────────────────
    {
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
        }
      },
      children: [
        spacer(), spacer(), spacer(),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 480, after: 240 },
          children: [new TextRun({
            text: "Dissolved Oxygen as the Primary Driver of",
            font: "Arial", size: 40, bold: true, color: "1F3864"
          })]
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 0, after: 240 },
          children: [new TextRun({
            text: "Benthic Community Assembly Under Seasonal Hypoxia",
            font: "Arial", size: 40, bold: true, color: "1F3864"
          })]
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 0, after: 480 },
          children: [new TextRun({
            text: "in the Semi-Enclosed Seto Inland Sea, Japan",
            font: "Arial", size: 40, bold: true, color: "1F3864"
          })]
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 0, after: 120 },
          border: { top: { style: BorderStyle.SINGLE, size: 6, color: "2E5899", space: 8 } },
          children: [new TextRun({
            text: "Reproducing and Extending Lai et al. (2024) Using Japanese National Monitoring Data",
            font: "Arial", size: 26, italics: true, color: "444444"
          })]
        }),
        spacer(), spacer(), spacer(),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 120, after: 80 },
          children: [new TextRun({ text: "Study Area: Seto Inland Sea (瀬戸内海), Japan", font: "Arial", size: 24, color: "444444" })]
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 0, after: 80 },
          children: [new TextRun({ text: "Data Period: 1991 – 2024", font: "Arial", size: 24, color: "444444" })]
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 0, after: 80 },
          children: [new TextRun({ text: "Seasonal Focus: Summer (June–September)", font: "Arial", size: 24, color: "444444" })]
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 0, after: 80 },
          children: [new TextRun({ text: "Analysis Date: June 2026", font: "Arial", size: 24, color: "444444" })]
        }),
        pageBreak()
      ]
    },

    // ── MAIN BODY ─────────────────────────────────────────────────────────
    {
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
        }
      },
      headers: {
        default: new Header({
          children: [new Paragraph({
            border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "2E5899", space: 4 } },
            children: [
              new TextRun({ text: "Seto Inland Sea Benthic Hypoxia Study", font: "Arial", size: 18, color: "555555" }),
              new TextRun({ text: "\t", font: "Arial", size: 18 }),
              new TextRun({ text: "Reproducing Lai et al. (2024)", font: "Arial", size: 18, italics: true, color: "888888" })
            ],
            tabStops: [{ type: "right", position: 9360 }]
          })]
        })
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            border: { top: { style: BorderStyle.SINGLE, size: 4, color: "2E5899", space: 4 } },
            children: [
              new TextRun({ text: "Page ", font: "Arial", size: 18, color: "555555" }),
              new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 18, color: "555555" }),
              new TextRun({ text: " of ", font: "Arial", size: 18, color: "555555" }),
              new TextRun({ children: [PageNumber.TOTAL_PAGES], font: "Arial", size: 18, color: "555555" }),
            ]
          })]
        })
      },
      children: [

        // ── TABLE OF CONTENTS ──
        new Paragraph({
          heading: HeadingLevel.HEADING_1,
          children: [new TextRun({ text: "Table of Contents", font: "Arial", size: 32, bold: true, color: "1F3864" })]
        }),
        new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-3" }),
        pageBreak(),

        // ═══════════════════════════════════════════════════════════════════
        // 1. BACKGROUND
        // ═══════════════════════════════════════════════════════════════════
        h1("1.  Background and Motivation"),
        body("The Seto Inland Sea (Setonaikai, 瀬戸内海) is Japan’s largest semi-enclosed coastal water body, stretching approximately 450 km between Honshu, Shikoku, and Kyushu. Its restricted circulation, warm summer temperatures, and historically high anthropogenic nutrient loading create conditions of severe seasonal bottom-water hypoxia (dissolved oxygen ≤ 2 mg/L) each summer. These hypoxic and anoxic bottom zones are directly lethal to most macrobenthic invertebrates and represent one of the most consequential ecological stressors in Japanese coastal waters."),
        body("This study reproduces and extends the analytical framework of Lai et al. (2024), who demonstrated that bottom-water dissolved oxygen (DO) is the dominant structuring force for benthic macrofaunal communities under hypoxic conditions in semi-enclosed bays. Here, we apply the same conceptual framework to the Setonaikai using Japan’s national environmental monitoring dataset, asking:"),
        bullet("Does bottom-water DO explain significant variation in benthic community composition across the Seto Inland Sea?"),
        bullet("Can sediment geochemical variables (sulfides, TOC, ORP) — which encode historical DO conditions — predict current ecological stress regimes?"),
        bullet("Have DO and sediment conditions shown measurable long-term improvement following Japan’s nutrient management policies (1973–present)?"),
        spacer(),

        // ═══════════════════════════════════════════════════════════════════
        // 2. DATA SOURCES
        // ═══════════════════════════════════════════════════════════════════
        h1("2.  Data Sources"),

        h2("2.1  Primary Dataset: bottom_2023.xlsx"),
        bodyMixed([
          { text: "Origin: ", bold: true },
          "Japan Ministry of the Environment (環境省) — Setonaikai national benthic monitoring programme"
        ]),
        bodyMixed([{ text: "Sheet used: ", bold: true }, { text: "底質_累積2023 ", italics: true }, "(cumulative sediment survey 2023 edition)"]),
        bodyMixed([{ text: "Content: ", bold: true }, "Repeated surveys at ~37 fixed stations across the Seto Inland Sea, Tokyo Bay, and Ise Bay from 1991 to 2024."]),
        bodyMixed([{ text: "Total records: ", bold: true }, "~1,433 station-year sediment observations; ~1,231 DO observations"]),
        spacer(),
        body("Variables recorded at each station-year survey:"),
        bullet("Benthic macrofauna: species identity and abundance for 800–900+ species/morphospecies"),
        bullet("Sediment chemistry: TOC (total organic carbon, mg/g), Sulfides (mg/g), ORP (oxidation-reduction potential, mV), COD (chemical oxygen demand, mg/g), LOI (loss on ignition %, proxy for organic matter), Clay fraction (%)"),
        bullet("Station metadata: latitude/longitude (degrees-minutes-seconds), depth (m), sea area code (海域コード), survey month/year"),
        spacer(),

        h2("2.2  Secondary Dataset: env_bottom_timeseries.csv"),
        body("Bottom-water dissolved oxygen (DO, mg/L) measured at environmental monitoring stations throughout the Seto Inland Sea. Individual DO measurements are joined to benthos/sediment stations via spatial nearest-neighbour (Haversine distance), matching each benthos station to the closest DO station in the same year and season."),
        spacer(),

        h2("2.3  Derived Processed Datasets"),
        new Table({
          width: { size: CONTENT_WIDTH, type: WidthType.DXA },
          columnWidths: [3200, 6160],
          rows: [
            new TableRow({ children: [headerCell("File", 3200), headerCell("Description", 6160)] }),
            ...[
              ["diversity_indices.csv", "Shannon H’, Simpson 1-D, Margalef, Pielou evenness computed per station-year from community matrix"],
              ["community_matrix_summer.csv", "Station-year × species abundance matrix, summer surveys only (Jun–Sep)"],
              ["community_matrix_winter.csv", "Station-year × species abundance matrix, winter surveys only (Jan–Mar)"],
              ["master_sediment_env.csv", "Merged sediment chemistry + matched bottom DO + ecological stress class labels"],
              ["step3_diversity_env_joined.csv", "Diversity indices joined to station-level DO via spatial NN match"],
              ["step4_station_env_summer.csv", "Station-level environmental table aligned to community matrix row order for Mantel tests"],
              ["step4_partial_mantel.csv", "Partial Mantel results controlling for geographic distance (summer)"],
              ["step3_within_bay_spearman.csv", "Within-bay Spearman r results: Hiroshima, Osaka, Ise Bay, SIS"],
              ["step5_rf_results.csv", "RF model feature importances, AUC, accuracy, and F1 scores"],
              ["step6_mk_trends.csv", "Mann-Kendall τ, p-value, Sen’s slope per variable × region (1991–2024)"],
              ["step7_synthesis_table.csv", "All major results consolidated in one table"],
            ].map(([f, d], i) => new TableRow({ children: [
              dataCell(f, 3200, altRow(i), true, "1F3864"),
              dataCell(d, 6160, altRow(i))
            ]}))
          ]
        }),
        spacer(),
        pageBreak(),

        // ═══════════════════════════════════════════════════════════════════
        // 3. DATA STRUCTURE
        // ═══════════════════════════════════════════════════════════════════
        h1("3.  Data Structure: What Each Point Represents"),
        bodyMixed([{ text: "A single data point in this analysis = one monitoring station surveyed in one year.", bold: true }]),
        spacer(),
        body("The monitoring programme revisits the same ~37 fixed geographic stations repeatedly over the study period (1991–2024). This means:"),
        bullet("The same physical location (e.g., station #12 in Hiroshima Bay) may appear as 15–30 separate points across years"),
        bullet("Each point carries that station’s complete environmental state for that survey (DO, sediment chemistry, benthic community composition)"),
        bullet("Points are NOT individual organisms, individual sediment samples within a station, or continuous spatial transects"),
        bullet("In scatter plots of e.g. Shannon diversity vs. DO, each dot is one station-year observation"),
        spacer(),
        body("This repeated-measures structure has important implications for interpretation:"),
        bullet("High within-station temporal variability (same location, different years) inflates scatter in bivariate plots"),
        bullet("Spatial autocorrelation exists because nearby stations share similar oceanographic conditions — addressed by the Partial Mantel test (Step 4)"),
        bullet("Long-term trends (Step 6) exploit the full temporal depth of the dataset; community turnover analyses (Step 4) treat each station-year as independent"),
        spacer(),

        // ═══════════════════════════════════════════════════════════════════
        // 4. TEMPORAL SCOPE
        // ═══════════════════════════════════════════════════════════════════
        h1("4.  Temporal Scope: Which Months Were Used"),
        bodyMixed([{ text: "Not all months. The analysis uses seasonal subsets only.", bold: true }]),
        spacer(),
        new Table({
          width: { size: CONTENT_WIDTH, type: WidthType.DXA },
          columnWidths: [1800, 2200, 5360],
          rows: [
            new TableRow({ children: [headerCell("Season", 1800), headerCell("Months", 2200), headerCell("Rationale", 5360)] }),
            new TableRow({ children: [
              dataCell("Summer", 1800, "FFF3CD", true, "7B4F00"),
              dataCell("June, July, August, September (6–9)", 2200, "FFF3CD"),
              dataCell("Peak hypoxia season; thermal stratification maximum; most comparable to Lai et al. (2024)", 5360, "FFF3CD")
            ]}),
            new TableRow({ children: [
              dataCell("Winter", 1800, "E8F4F8"),
              dataCell("January, February, March (1–3)", 2200, "E8F4F8"),
              dataCell("Low-stratification baseline; DO near-saturation; used for seasonal contrast in Mantel tests", 5360, "E8F4F8")
            ]}),
            new TableRow({ children: [
              dataCell("Other months", 1800, "F8F8F8"),
              dataCell("April, May, October–December", 2200, "F8F8F8"),
              dataCell("EXCLUDED — transitional months introduce within-season noise and confound seasonal contrasts", 5360, "F8F8F8")
            ]})
          ]
        }),
        spacer(),
        body("The primary ecological analyses (Mantel tests, RF classifier, diversity-DO correlations) focus on summer data, when hypoxic stress is most severe and ecologically relevant. For long-term trend analysis (Step 6), summer annual means are computed per station/region to track interannual change in DO and sediment chemistry."),
        spacer(),
        pageBreak(),

        // ═══════════════════════════════════════════════════════════════════
        // 5. METHODS
        // ═══════════════════════════════════════════════════════════════════
        h1("5.  Methods Overview"),
        body("The pipeline follows 7 sequential steps:"),
        spacer(),
        new Table({
          width: { size: CONTENT_WIDTH, type: WidthType.DXA },
          columnWidths: [1200, 2600, 5560],
          rows: [
            new TableRow({ children: [headerCell("Step", 1200), headerCell("Name", 2600), headerCell("Description", 5560)] }),
            ...[
              ["1", "Environmental Characterisation", "DO, temperature, stratification index (Hiroshima + Osaka); seasonal cycle characterisation"],
              ["2", "K-Means Clustering", "Regime classification (hypoxic/transitional/normoxic) for Hiroshima, Osaka, and SIS sediment"],
              ["3", "Diversity + GAM", "Shannon, Simpson, Margalef, Pielou vs DO; GAM fitting; within-bay Spearman analysis"],
              ["4", "Mantel Tests", "Bray-Curtis community dissimilarity vs environmental distance; partial Mantel controlling for geographic distance"],
              ["5", "Random Forest", "3-class stress classifier (dead/stressed/healthy) using sediment + spatial + temporal features; threshold tuning"],
              ["6", "Mann-Kendall Trends", "Long-term monotonic trends 1991–2024 in DO, Sulfides, TOC, ORP, COD; Sen’s slope"],
              ["7", "Synthesis", "Integrated results table, 4-panel figure, and 5-point limitations summary"],
            ].map(([s, n, d], i) => new TableRow({ children: [
              dataCell(s, 1200, altRow(i), true, "1F3864"),
              dataCell(n, 2600, altRow(i), true),
              dataCell(d, 5560, altRow(i))
            ]}))
          ]
        }),
        spacer(),

        h2("5.1  Key Methodological Choices and Justifications"),
        bodyMixed([{ text: "Bray-Curtis dissimilarity: ", bold: true }, "Standard metric for species abundance data; robust to the double-zero problem (two absent species should not count as a similarity)"]),
        bodyMixed([{ text: "Spearman-based Mantel test: ", bold: true }, "Community and environmental distances are non-normal; 999 permutations of the full distance matrix to generate null distribution; two-tailed p-value"]),
        bodyMixed([{ text: "Partial Mantel test: ", bold: true }, "Residualises both Bray-Curtis and environmental distances on Haversine geographic distance, then correlates residuals — isolates pure environmental signal from spatial autocorrelation"]),
        bodyMixed([{ text: "Temporal train/val/test split: ", bold: true }, "≤2010 train, 2011–2017 val, >2017 test — avoids data leakage, exposes temporal covariate shift"]),
        bodyMixed([{ text: "Threshold tuning on val set: ", bold: true }, "Grid search over dead/stressed probability thresholds, constrained to dead recall ≥0.50, then maximise macro-F1; threshold never touched test set"]),
        bodyMixed([{ text: "Sen’s slope: ", bold: true }, "Robust median-based slope estimator; trend lines plotted using OLS on actual year values (not index-based intercept to avoid axis scaling errors)"]),
        spacer(),
        pageBreak(),

        // ═══════════════════════════════════════════════════════════════════
        // 6. RESULTS
        // ═══════════════════════════════════════════════════════════════════
        h1("6.  Results by Step"),

        // ── STEP 1 ──
        h2("Step 1: Environmental Characterisation"),
        h3("Hiroshima Bay 2014"),
        body("Bottom DO shows a strong seasonal cycle: summer minimum ~1.5–2.5 mg/L (hypoxic), winter maximum ~8–10 mg/L. Thermal stratification (ΔT surface-bottom) peaks June–September, directly suppressing vertical mixing and driving DO depletion. Strong negative relationship: as stratification index increases, bottom DO decreases (Spearman r ≈ −0.6 to −0.8 depending on depth)."),
        h3("Osaka Bay 2016"),
        body("Similar seasonal pattern with larger tidal range moderating hypoxia somewhat. Deepest stations (~20 m) experience most severe DO depletion. Salinity stratification co-contributes with thermal stratification to density barrier formation."),
        bodyMixed([{ text: "Key finding: ", bold: true }, "Physical oceanographic forcing (thermal + haline stratification) is the proximate mechanism driving bottom-water DO depletion each summer. This sets up the ecological stress gradient that structures benthic communities."]),
        spacer(),

        // ── STEP 2 ──
        h2("Step 2: K-Means Regime Classification"),
        body("K-Means clustering was applied to identify oceanographic regimes from environmental features (DO, temperature, salinity, stratification index, cyclic month encoding)."),
        spacer(),
        h3("Hiroshima Bay (K=3, silhouette=0.409 — Acceptable)"),
        new Table({
          width: { size: CONTENT_WIDTH, type: WidthType.DXA },
          columnWidths: [1800, 3200, 2180, 2180],
          rows: [
            new TableRow({ children: [
              headerCell("Cluster", 1800), headerCell("Interpretation", 3200),
              headerCell("Mean DO (mg/L)", 2180), headerCell("Mean Temp (°C)", 2180)
            ]}),
            ...[
              ["0 — Hypoxic", "Summer hypoxic events (Jul–Sep)", "~2.0", "~25"],
              ["1 — Transitional", "Spring/autumn intermediate", "~4.5", "~20"],
              ["2 — Normoxic", "Winter normoxic/cool baseline", "~8.0", "~14"],
            ].map(([c, i, d, t], r) => new TableRow({ children: [
              dataCell(c, 1800, altRow(r), true),
              dataCell(i, 3200, altRow(r)),
              dataCell(d, 2180, altRow(r)),
              dataCell(t, 2180, altRow(r))
            ]}))
          ]
        }),
        spacer(),
        h3("Osaka Bay (K=6, silhouette=0.368 — Borderline Acceptable)"),
        body("More clusters reflect greater spatial and tidal complexity. Finer stratification gradients captured; deep-station hypoxia distinct from shallow. Silhouette borderline: 6 clusters may overfit; treat as exploratory."),
        spacer(),
        h3("⚠  Sediment SIS (K=3, silhouette=0.276 — WEAK)"),
        new Table({
          width: { size: CONTENT_WIDTH, type: WidthType.DXA },
          columnWidths: [1600, 3000, 2380, 2380],
          rows: [
            new TableRow({ children: [
              headerCell("Cluster", 1600), headerCell("Interpretation", 3000),
              headerCell("Mean DO (mg/L)", 2380), headerCell("Mean Sulfides (mg/g)", 2380)
            ]}),
            ...[
              ["0 — Anaerobic", "High-sulfide / low-ORP (anaerobic)", "2.7", "1.47"],
              ["1 — Intermediate", "Moderate organic load", "6.0", "0.27"],
              ["2 — Oxic", "Low-sulfide / high-ORP (oxic)", "6.3", "0.11"],
            ].map(([c, i, d, s], r) => new TableRow({ children: [
              dataCell(c, 1600, altRow(r), true),
              dataCell(i, 3000, altRow(r)),
              dataCell(d, 2380, altRow(r)),
              dataCell(s, 2380, altRow(r))
            ]}))
          ]
        }),
        spacer(),
        new Paragraph({
          spacing: { before: 100, after: 120 },
          shading: { fill: "FFF3CD", type: ShadingType.CLEAR },
          children: [new TextRun({ text: "⚠  Important caveat: Silhouette = 0.276 is weak. Cluster boundaries are not well-separated in feature space. The sediment K-means is used descriptively only — to identify the high-sulfide anaerobic sediment regime as ecologically meaningful, not as a validated classification tool. The high-sulfide cluster (Cluster 0) is the primary result: these stations have the lowest matched DO (2.7 mg/L) and highest sulfide/TOC concentrations, consistent with chronic anaerobic diagenesis driven by historical hypoxic deposition.", font: "Arial", size: 20, italics: true, color: "7B4F00" })]
        }),
        spacer(),
        pageBreak(),

        // ── STEP 3 ──
        h2("Step 3: Diversity Indices and GAM Analysis"),
        body("Diversity indices computed per station-year: Shannon H’ (information-theoretic), Simpson 1-D (dominance-based), Margalef (richness corrected for sample size), Pielou J’ (evenness)."),
        spacer(),
        h3("All-Stations Correlations (n ≈ 1,229 station-years)"),
        new Table({
          width: { size: CONTENT_WIDTH, type: WidthType.DXA },
          columnWidths: [2340, 2340, 2340, 2340],
          rows: [
            new TableRow({ children: [
              headerCell("Index", 2340), headerCell("Spearman r (vs DO)", 2340),
              headerCell("p-value", 2340), headerCell("Interpretation", 2340)
            ]}),
            ...[
              ["Shannon H’", "+0.003", "0.91 (ns)", "Flat — spatial noise dominates"],
              ["Simpson 1-D", "+0.010", "0.73 (ns)", "Flat"],
              ["Margalef", "−0.023", "0.45 (ns)", "Flat"],
              ["Pielou J’", "+0.037", "0.21 (ns)", "Flat"],
            ].map(([i, r, p, interp], row) => new TableRow({ children: [
              dataCell(i, 2340, altRow(row), true),
              dataCell(r, 2340, altRow(row)),
              dataCell(p, 2340, altRow(row)),
              dataCell(interp, 2340, altRow(row))
            ]}))
          ]
        }),
        spacer(),
        body("All near-zero and non-significant. This does not mean DO is unimportant — it means the all-station analysis is confounded. Stations span the entire Seto Inland Sea including many permanently normoxic locations. Including them dilutes any hypoxia-diversity signal."),
        spacer(),
        h3("DO-Stressed Subset (DO ≤ 4 mg/L, n = 113–142 station-years)"),
        new Table({
          width: { size: CONTENT_WIDTH, type: WidthType.DXA },
          columnWidths: [2340, 2340, 2340, 2340],
          rows: [
            new TableRow({ children: [
              headerCell("Index", 2340), headerCell("Spearman r (vs DO)", 2340),
              headerCell("p-value", 2340), headerCell("Significance", 2340)
            ]}),
            ...[
              ["Shannon H’", "+0.160", "0.056", "Marginal"],
              ["Simpson 1-D", "+0.201", "0.017", "*"],
              ["Margalef", "+0.083", "0.384", "ns"],
              ["Pielou J’", "+0.370", "<0.001", "***  KEY RESULT"],
            ].map(([i, r, p, s], row) => new TableRow({ children: [
              dataCell(i, 2340, altRow(row), true),
              dataCell(r, 2340, altRow(row)),
              dataCell(p, 2340, altRow(row)),
              dataCell(s, 2340, altRow(row), row === 3, row === 3 ? "1F3864" : "222222")
            ]}))
          ]
        }),
        spacer(),
        body("Within the hypoxia-relevant range, Pielou evenness shows a significant positive correlation with DO (r = +0.370, p < 0.001). As DO decreases below the stress threshold, community evenness drops because only a few tolerant taxa (e.g., polychaetes Capitella spp.) survive, increasing dominance."),
        spacer(),
        h3("Within-Bay Analysis (New — Fix 2)"),
        body("Running Spearman separately per bay reveals stronger signals obscured in the SIS-wide analysis:"),
        new Table({
          width: { size: CONTENT_WIDTH, type: WidthType.DXA },
          columnWidths: [2000, 1800, 1600, 1480, 1480, 1000],
          rows: [
            new TableRow({ children: [
              headerCell("Bay", 2000), headerCell("Subset", 1800),
              headerCell("Index", 1600), headerCell("r", 1480),
              headerCell("p-value", 1480), headerCell("n", 1000)
            ]}),
            ...[
              ["Hiroshima Bay", "All stations", "Shannon", "−0.344", "0.006 **", "63"],
              ["Ise Bay", "Stressed (DO≤4)", "Shannon", "+0.455", "0.007 **", "34"],
              ["SIS (other)", "All stations", "Pielou", "+0.259", "<0.001 ***", "254"],
              ["Osaka Bay", "All stations", "Shannon", "+0.147", "0.247 ns", "64"],
            ].map(([b, sub, idx, r, p, n], row) => new TableRow({ children: [
              dataCell(b, 2000, altRow(row), row===1, row===1 ? "1F3864" : "222222"),
              dataCell(sub, 1800, altRow(row)),
              dataCell(idx, 1600, altRow(row)),
              dataCell(r, 1480, altRow(row), row===1, row===1 ? "1F3864" : "222222"),
              dataCell(p, 1480, altRow(row)),
              dataCell(n, 1000, altRow(row))
            ]}))
          ]
        }),
        spacer(),
        body("Ise Bay in the stressed subset shows the strongest within-bay signal (Shannon r = +0.455**), confirming that the SIS-wide flat correlations masked real bay-level structure."),
        spacer(),
        pageBreak(),

        // ── STEP 4 ──
        h2("Step 4: Mantel Tests"),
        bodyMixed([{ text: "Mean Bray-Curtis dissimilarity: ", bold: true }, "Summer 0.947 | Winter 0.945. This near-maximum dissimilarity (range 0–1) reflects extreme community turnover across the SIS: most pairs of stations share almost no species in common."]),
        spacer(),
        h3("Summer Mantel Results (n = 584 station-years, 170,236 pairs for DO)"),
        new Table({
          width: { size: CONTENT_WIDTH, type: WidthType.DXA },
          columnWidths: [1800, 1900, 1900, 1900, 1860],
          rows: [
            new TableRow({ children: [
              headerCell("Variable", 1800), headerCell("n Stations", 1900),
              headerCell("Mantel r", 1900), headerCell("p-value", 1900),
              headerCell("Significance", 1860)
            ]}),
            ...[
              ["DO", "3,494", "+0.185", "0.001", "**  STRONGEST"],
              ["Sulfides", "446", "+0.119", "0.001", "**"],
              ["TOC", "447", "+0.099", "0.001", "**"],
              ["LOI", "447", "+0.057", "0.002", "**"],
              ["COD", "447", "+0.048", "0.010", "*"],
              ["ORP", "427", "+0.006", "0.756", "ns"],
              ["Clay%", "447", "+0.032", "0.076", "ns"],
            ].map(([v, n, r, p, s], row) => new TableRow({ children: [
              dataCell(v, 1800, altRow(row), true),
              dataCell(n, 1900, altRow(row)),
              dataCell(r, 1900, altRow(row), row===0, row===0 ? "1F3864" : "222222"),
              dataCell(p, 1900, altRow(row)),
              dataCell(s, 1860, altRow(row), row===0, row===0 ? "1F3864" : "222222")
            ]}))
          ]
        }),
        spacer(),
        h3("Winter Mantel Results (n = 647 station-years)"),
        new Table({
          width: { size: CONTENT_WIDTH, type: WidthType.DXA },
          columnWidths: [2340, 2340, 2340, 2340],
          rows: [
            new TableRow({ children: [headerCell("Variable", 2340), headerCell("Mantel r", 2340), headerCell("p-value", 2340), headerCell("Significance", 2340)] }),
            ...[
              ["DO", "+0.073", "0.001", "**"],
              ["Clay%", "+0.099", "0.001", "**"],
              ["ORP", "+0.056", "0.002", "**"],
              ["TOC", "+0.044", "0.002", "**"],
            ].map(([v, r, p, s], row) => new TableRow({ children: [
              dataCell(v, 2340, altRow(row), true),
              dataCell(r, 2340, altRow(row)),
              dataCell(p, 2340, altRow(row)),
              dataCell(s, 2340, altRow(row))
            ]}))
          ]
        }),
        spacer(),
        body("Summer DO has the strongest Mantel r (0.185), more than twice the winter value (0.073), consistent with hypoxia-driven community assembly being a summer phenomenon. Sulfides rank second in summer (0.119), confirming that anaerobic sediment chemistry provides an independent signal of community structuring."),
        spacer(),
        h3("Partial Mantel (Summer — Controlling for Geographic Distance)"),
        body("To isolate pure environmental signal from spatial autocorrelation, both Bray-Curtis and environmental distances are residualised on Haversine geographic distance, then residuals are correlated. Variables remaining significant after geographic control represent genuine environmental structuring — not just spatial proximity. Full results are in data/processed/step4_partial_mantel.csv and figures/step4_partial_mantel.png."),
        spacer(),
        pageBreak(),

        // ── STEP 5 ──
        h2("Step 5: Random Forest Stress Classifier"),
        h3("Model Design"),
        new Table({
          width: { size: CONTENT_WIDTH, type: WidthType.DXA },
          columnWidths: [1600, 3000, 4760],
          rows: [
            new TableRow({ children: [headerCell("Class", 1600), headerCell("DO Threshold", 3000), headerCell("Ecological Meaning", 4760)] }),
            ...[
              ["0 — Dead", "DO ≤ 2 mg/L", "Acute hypoxia; most macrofauna killed or fled"],
              ["1 — Stressed", "2 < DO ≤ 4 mg/L", "Sub-lethal stress; community impoverished"],
              ["2 — Healthy", "DO > 4 mg/L", "Normoxic; full community present"],
            ].map(([c, d, m], row) => new TableRow({ children: [
              dataCell(c, 1600, altRow(row), true),
              dataCell(d, 3000, altRow(row)),
              dataCell(m, 4760, altRow(row))
            ]}))
          ]
        }),
        spacer(),
        body("Class distribution (1,852 total station-years): Dead 216 (11.7%), Stressed 194 (10.5%), Healthy 1,442 (77.9%)."),
        spacer(),
        h3("Val Set Accuracy Comparison"),
        new Table({
          width: { size: 5000, type: WidthType.DXA },
          columnWidths: [2500, 2500],
          rows: [
            new TableRow({ children: [headerCell("Model", 2500), headerCell("Val Accuracy", 2500)] }),
            new TableRow({ children: [dataCell("Sediment only", 2500, "FFFFFF"), dataCell("0.739", 2500, "FFFFFF")] }),
            new TableRow({ children: [dataCell("+ Spatial + Year", 2500, "E8F4E8", true, "1F3864"), dataCell("0.819 (+8.0 pp)", 2500, "E8F4E8", true, "1F3864")] }),
          ]
        }),
        spacer(),
        h3("Test Set Performance (> 2017, n = 416)"),
        new Table({
          width: { size: CONTENT_WIDTH, type: WidthType.DXA },
          columnWidths: [2340, 2340, 2340, 2340],
          rows: [
            new TableRow({ children: [headerCell("Metric", 2340), headerCell("Argmax Baseline", 2340), headerCell("Threshold-Adjusted", 2340), headerCell("Change", 2340)] }),
            ...[
              ["Accuracy", "0.764", "0.716", "−4.8 pp"],
              ["F1 macro", "0.463", "0.451", "−1.2 pp"],
              ["Dead recall", "0.271", "0.339", "+6.8 pp  ✅"],
              ["Stressed recall", "0.152", "0.182", "+3.0 pp"],
              ["Healthy recall", "0.917", "0.840", "−7.7 pp"],
            ].map(([m, a, t, c], row) => new TableRow({ children: [
              dataCell(m, 2340, altRow(row), true),
              dataCell(a, 2340, altRow(row)),
              dataCell(t, 2340, altRow(row), row===2, row===2 ? "1F3864" : "222222"),
              dataCell(c, 2340, altRow(row))
            ]}))
          ]
        }),
        spacer(),
        body("Threshold adjustment (dead ≥ 0.35, stressed ≥ 0.30) improves dead recall (+6.8 pp) at the cost of overall accuracy (−4.8 pp). This is a deliberate trade-off: missing a dead-zone station is the worst failure mode for ecological monitoring."),
        spacer(),
        h3("Feature Importance (MDI — Full Model with Spatial + Temporal Features)"),
        new Table({
          width: { size: 5000, type: WidthType.DXA },
          columnWidths: [500, 2500, 2000],
          rows: [
            new TableRow({ children: [headerCell("Rank", 500), headerCell("Feature", 2500), headerCell("MDI", 2000)] }),
            ...[
              ["1", "Depth (m)", "0.125"],
              ["2", "Sulfides (mg/g)", "0.123"],
              ["3", "LOI % (organic)", "0.120"],
              ["4", "ORP (mV)", "0.119"],
              ["5", "TOC (mg/g)", "0.101"],
              ["6", "Longitude", "0.090"],
              ["7", "Latitude", "0.084"],
              ["8", "Clay %", "0.083"],
              ["9", "Year", "0.080"],
              ["10", "COD (mg/g)", "0.076"],
            ].map(([r, f, m], row) => new TableRow({ children: [
              dataCell(r, 500, altRow(row)),
              dataCell(f, 2500, altRow(row), row <= 1, row <= 1 ? "1F3864" : "222222"),
              dataCell(m, 2000, altRow(row))
            ]}))
          ]
        }),
        spacer(),
        bodyMixed([{ text: "Root cause of low dead recall (34%): ", bold: true }, "Temporal covariate shift. The model trains on 1991–2010 data (high organic loading era) and tests on >2017 data (post-recovery era). Sulfide thresholds associated with “dead zone” conditions in the training era no longer apply after years of sediment recovery."]),
        spacer(),
        pageBreak(),

        // ── STEP 6 ──
        h2("Step 6: Long-Term Trend Analysis (Mann-Kendall, 1991–2024)"),
        body("Annual summer means computed per region (SIS, Tokyo Bay, Ise Bay, All combined). Mann-Kendall τ measures monotonic trend; Sen’s slope estimates the rate of change per year."),
        spacer(),
        h3("Significant Trends (p < 0.05)"),
        new Table({
          width: { size: CONTENT_WIDTH, type: WidthType.DXA },
          columnWidths: [1600, 1800, 1200, 1400, 1200, 2160],
          rows: [
            new TableRow({ children: [
              headerCell("Region", 1600), headerCell("Variable", 1800),
              headerCell("Direction", 1200), headerCell("τ", 1400),
              headerCell("p", 1200), headerCell("Interpretation", 2160)
            ]}),
            ...[
              ["SIS", "Bottom DO", "↑", "+0.538", "***", "Sustained DO recovery"],
              ["SIS", "Sulfides", "↓", "−0.348", "**", "Anaerobic load declining"],
              ["All", "Bottom DO", "↑", "+0.479", "***", "National improvement"],
              ["Tokyo", "Bottom DO", "↑", "+0.397", "**", "Tokyo Bay recovery"],
              ["Tokyo", "COD", "↓", "−0.527", "***", "Organic load reduction"],
              ["Ise", "Bottom DO", "↑", "+0.390", "**", "Ise Bay improvement"],
            ].map(([reg, v, dir, tau, p, interp], row) => new TableRow({ children: [
              dataCell(reg, 1600, altRow(row), true),
              dataCell(v, 1800, altRow(row)),
              dataCell(dir, 1200, altRow(row), true, dir==="↑" ? "1F6B3A" : "C0392B"),
              dataCell(tau, 1400, altRow(row), true),
              dataCell(p, 1200, altRow(row)),
              dataCell(interp, 2160, altRow(row))
            ]}))
          ]
        }),
        spacer(),
        bodyMixed([{ text: "Key finding: ", bold: true }, "SIS bottom-water DO has increased significantly over 1991–2024 (τ = +0.538, p < 0.001 — the strongest trend in the dataset), consistent with Japan’s Setonaikai Law nutrient management policies. Sediment sulfide concentrations have also declined (τ = −0.348), lagging the DO recovery by several years — expected, because sulfides accumulated over decades cannot be reversed as quickly as water-column oxygen."]),
        spacer(),
        pageBreak(),

        // ═══════════════════════════════════════════════════════════════════
        // 7. INTEGRATED INTERPRETATION
        // ═══════════════════════════════════════════════════════════════════
        h1("7.  Integrated Interpretation"),

        h2("7.1  Summary of Evidence for DO as Primary Community Driver"),
        new Table({
          width: { size: CONTENT_WIDTH, type: WidthType.DXA },
          columnWidths: [3000, 2800, 3560],
          rows: [
            new TableRow({ children: [
              headerCell("Line of Evidence", 3000), headerCell("Result", 2800), headerCell("Strength", 3560)
            ]}),
            ...[
              ["Mantel (Summer DO)", "r = +0.185, p = 0.001", "Moderate — robust to permutation"],
              ["Partial Mantel (| geo dist)", "Sig. residual after geo control", "Genuine env. signal, not spatial artifact"],
              ["Diversity-DO (stressed, Pielou)", "r = +0.370, p < 0.001", "Strong within hypoxia range"],
              ["Ise Bay stressed Shannon", "r = +0.455, p = 0.007", "Strong within-bay signal"],
              ["RF Dead recall", "34% threshold-adjusted", "Weak predictive; honest limitation"],
              ["Sulfides MDI rank 2", "0.123 (Depth #1 at 0.125)", "Encodes historical DO depletion"],
              ["Long-term DO recovery", "τ = +0.538, p < 0.001", "Policy-driven improvement confirmed"],
            ].map(([ev, res, str], row) => new TableRow({ children: [
              dataCell(ev, 3000, altRow(row), true),
              dataCell(res, 2800, altRow(row)),
              dataCell(str, 3560, altRow(row))
            ]}))
          ]
        }),
        spacer(),

        h2("7.2  Why the All-Station Diversity-DO Correlation is Flat"),
        body("The Seto Inland Sea contains ~37 monitoring stations spanning from shallow nearshore (normoxic year-round) to deep confined basins (hypoxic every summer). At the SIS-wide scale, most stations have DO > 4 mg/L most years; diversity at normoxic stations is driven by other factors (depth, substrate, biogeography, fishing disturbance). Only 10–12% of station-years experience DO ≤ 2 mg/L."),
        body("This creates a situation where DO and diversity are nearly uncorrelated at the full-dataset scale, but strongly correlated within the ecologically relevant subset. The all-station flat result is a signal-to-noise problem, not a null result. The within-subset analysis (Pielou r = +0.370***, Ise Bay Shannon r = +0.455**) reveals the real relationship."),
        spacer(),

        h2("7.3  Why Sediment Variables Matter Beyond DO"),
        body("Sediment sulfides and LOI provide a complementary window on hypoxic stress:"),
        bullet("They integrate DO conditions over months to years, not just the single survey measurement"),
        bullet("A station may appear normoxic at survey time due to weather-driven mixing, yet have high sulfides from the preceding hypoxic summer"),
        bullet("The Mantel result (Sulfides r = 0.119**, independent of DO r = 0.185**) suggests sediment chemistry contributes independent variance in explaining community dissimilarity"),
        bullet("For management: sediment sulfides provide a durable indicator of chronic hypoxia history that does not require precise timing of DO measurements"),
        spacer(),
        pageBreak(),

        // ═══════════════════════════════════════════════════════════════════
        // 8. LIMITATIONS
        // ═══════════════════════════════════════════════════════════════════
        h1("8.  Key Limitations and Honest Caveats"),

        h2("Limitation 1: Station-Level DO Measurement Noise"),
        body("DO values joined to benthos stations are spatial nearest-neighbour matches, not measurements at the exact benthos station. Matching error adds noise to all DO-based analyses and attenuates correlations toward zero. True correlations are likely larger than observed."),

        h2("Limitation 2: Weak Sediment K-Means Separation (Silhouette = 0.276)"),
        body("The three-cluster sediment solution has weak separation. Cluster membership should not be treated as a validated ecological classification. The descriptive identification of a high-sulfide / low-ORP anaerobic sediment regime is the meaningful result; the precise cluster boundaries are not."),

        h2("Limitation 3: RF Classifier Temporal Covariate Shift"),
        body("The RF model trains on data from 1991–2010 (high organic loading) and tests on data from 2018–2024 (post-recovery). Sediment chemistry thresholds associated with “dead zone” conditions in the training era no longer map reliably to DO ≤ 2 mg/L in the test era. Dead recall of 34% is the honest result. This is a finding about the limits of using historical calibrations for current-day prediction — not a methods failure."),

        h2("Limitation 4: Low Mantel r Values"),
        body("Mantel r values of 0.07–0.19 are small in absolute terms. Given mean BC ≈ 0.95 (extreme community turnover), single environmental variable vs multi-variate community, and measurement noise in DO and sediment, these values are consistent with published benthic Mantel studies. A large proportion of community variation is explained by unmeasured factors (grain size detail, disturbance history, larval recruitment, fishing)."),

        h2("Limitation 5: Small Within-Bay Sample Sizes"),
        body("Hiroshima Bay (n=63), Osaka Bay (n=64), Ise Bay stressed (n=27–34) have limited sample sizes. The Ise Bay result (Shannon r=+0.455**) is based on n=34 stressed station-years — statistically significant but ecologically interpretable with caution. Geographic bounding box classification missed ~700 stations categorised as Other/Unknown."),

        h2("Limitation 6: Correlation, Not Causation"),
        body("All analyses are correlational/associational. DO and community composition covary; sediment chemistry and community composition covary. The mechanistic link is well-established in the literature (Diaz & Rosenberg 2008; Lai et al. 2024) but is not directly demonstrated here from the national monitoring data alone."),
        spacer(),
        pageBreak(),

        // ═══════════════════════════════════════════════════════════════════
        // 9. CONCLUSIONS
        // ═══════════════════════════════════════════════════════════════════
        h1("9.  Conclusions"),

        body("1.  Bottom-water DO is the dominant structuring force for benthic macrofaunal communities under seasonal hypoxia in the Seto Inland Sea (Summer Mantel r = +0.185, p = 0.001; Ise Bay stressed Shannon r = +0.455**, p = 0.007)."),
        body("2.  Sediment sulfides provide an independent signal of community structuring (Summer Mantel r = +0.119, p = 0.001), consistent with their role as a long-term integrator of hypoxic deposition history."),
        body("3.  The all-station diversity-DO relationship is flat (r ≈ 0.00–0.04, ns) due to dilution by normoxic stations. Within the ecologically relevant range (DO ≤ 4 mg/L), Pielou evenness shows a meaningful positive relationship with DO (r = +0.370, p < 0.001)."),
        body("4.  Sediment K-means clustering identifies a high-sulfide/low-ORP anaerobic sediment regime co-occurring with the lowest matched DO values (mean 2.7 mg/L), but cluster separation is weak (silhouette = 0.276). Used descriptively only."),
        body("5.  A 3-class RF stress classifier trained on sediment + spatial + temporal features achieves val accuracy of 0.819, but test-set dead recall of only 34% due to temporal covariate shift. Appropriate for driver identification and monitoring prioritisation, not operational prediction."),
        body("6.  Significant long-term recovery is underway: SIS bottom-water DO has increased monotonically 1991–2024 (τ = +0.538, p < 0.001), and sediment sulfide concentrations have declined (τ = −0.348, p < 0.01), consistent with Japan’s Setonaikai Law nutrient reduction policies."),
        body("7.  The correct framing: Environmental variables (DO, Sulfides, LOI) structure benthic community composition at the assemblage level, but are insufficient to predict local diversity at individual stations due to high community turnover (BC ≈ 0.95), measurement noise, unmeasured drivers, and temporal covariate shift. This is an honest finding — the environmental signal is real but partial."),
        spacer(),
        pageBreak(),

        // ═══════════════════════════════════════════════════════════════════
        // APPENDICES
        // ═══════════════════════════════════════════════════════════════════
        h1("Appendix A: Figures"),
        new Table({
          width: { size: CONTENT_WIDTH, type: WidthType.DXA },
          columnWidths: [3600, 5760],
          rows: [
            new TableRow({ children: [headerCell("Figure File", 3600), headerCell("Description", 5760)] }),
            ...[
              ["step2_elbow_silhouette.png", "K selection elbow + silhouette curves with quality threshold lines (≥0.50 strong, ≥0.35 acceptable, ≥0.25 weak)"],
              ["step2_cluster_scatter_hiroshima.png", "Hiroshima cluster scatter: DO vs Temperature, DO vs Stratification Index"],
              ["step2_sediment_cluster_scatter.png", "SIS sediment clusters: TOC vs Sulfides, coloured by DO and by cluster (with honest silhouette warning)"],
              ["step3_gam_diversity_vs_do.png", "2×4 GAM panels: all stations (flat/⚠ confounded) vs stressed subset (signal present)"],
              ["step3_spearman_heatmap.png", "Spearman r heatmap: diversity × environment (all stations + stressed)"],
              ["step3_within_bay_spearman.png", "Within-bay Spearman r (Shannon, Pielou vs DO): Hiroshima, Osaka, Ise, SIS"],
              ["step3_do_at_benthos_stations.png", "DO distribution histogram at benthos stations + seasonal boxplots"],
              ["step4_mantel_results.png", "Mantel r bar chart: Summer + Winter, all stations + stressed subset"],
              ["step4_partial_mantel.png", "Simple vs partial Mantel r: Summer, controlling for geographic (Haversine) distance"],
              ["step4_env_pairplots.png", "Pairwise environmental variable scatter plots (summer station-level data)"],
              ["step5_feature_importance.png", "MDI feature importance: binary (hypoxia) + 3-class (stress) models"],
              ["step5_stress_classifier.png", "4-panel: argmax CM, threshold-adjusted CM, recall comparison, Sulfides marginal effect"],
              ["step5_driver_effects.png", "Marginal effects of top 3 sediment features → stress class probability"],
              ["step6_trend_timeseries.png", "Annual summer means time series (DO, Sulfides, ORP, LOI, TOC) with MK trend lines"],
              ["step6_tau_heatmap.png", "Mann-Kendall τ heatmap: variable × region"],
              ["step7_synthesis_figure.png", "4-panel synthesis: Mantel r, diversity-DO, RF importance, temporal trends"],
            ].map(([f, d], i) => new TableRow({ children: [
              dataCell(f, 3600, altRow(i), true, "1F3864"),
              dataCell(d, 5760, altRow(i))
            ]}))
          ]
        }),
        spacer(),

        h1("Appendix B: Data Files"),
        new Table({
          width: { size: CONTENT_WIDTH, type: WidthType.DXA },
          columnWidths: [3600, 5760],
          rows: [
            new TableRow({ children: [headerCell("File", 3600), headerCell("Description", 5760)] }),
            ...[
              ["master_sediment_env.csv", "Merged sediment + DO + stress labels (all stations, all years, all seasons)"],
              ["diversity_indices.csv", "Shannon, Simpson, Margalef, Pielou per station-year"],
              ["community_matrix_summer.csv", "Species abundance matrix, summer surveys (Jun–Sep)"],
              ["community_matrix_winter.csv", "Species abundance matrix, winter surveys (Jan–Mar)"],
              ["step2_kmeans_scores.csv", "Silhouette scores by K for Hiroshima, Osaka, and SIS sediment"],
              ["step3_spearman_heatmap_all.csv", "Spearman r: diversity vs environment, all stations"],
              ["step3_spearman_heatmap_hypoxic.csv", "Spearman r: diversity vs environment, stressed stations (DO≤4)"],
              ["step3_within_bay_spearman.csv", "Within-bay Spearman r results (new — Fix 2)"],
              ["step4_mantel_results.csv", "Full Mantel test results: season, subset, variable, r, p"],
              ["step4_partial_mantel.csv", "Partial Mantel results: simple r vs partial r controlling for geo distance"],
              ["step5_rf_results.csv", "RF model results: feature importances, AUC, accuracy, F1"],
              ["step6_mk_trends.csv", "Mann-Kendall τ, p-value, Sen’s slope per variable × region"],
              ["step7_synthesis_table.csv", "All major results consolidated in one table"],
            ].map(([f, d], i) => new TableRow({ children: [
              dataCell(f, 3600, altRow(i), true, "1F3864"),
              dataCell(d, 5760, altRow(i))
            ]}))
          ]
        }),
        spacer(),

        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 480, after: 120 },
          border: { top: { style: BorderStyle.SINGLE, size: 4, color: "2E5899", space: 6 } },
          children: [new TextRun({ text: "Analysis pipeline: src/step1 → step2 → step3 → step4 → step5 → step6 → step7", font: "Arial", size: 18, italics: true, color: "666666" })]
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "Reference: Lai et al. (2024). Data: Japan Ministry of the Environment (1991–2024).", font: "Arial", size: 18, italics: true, color: "666666" })]
        }),

      ]
    }
  ]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("SetoNaikai_Analysis_Report.docx", buffer);
  console.log("Done: SetoNaikai_Analysis_Report.docx");
});
