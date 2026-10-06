# PixelRAG GeoGuessr Experiment Log

This file records the completed research workflow and the decisions that materially affected the final evaluation.

## Project setup

- Project: PixelRAG for GeoGuessr
- Environment verified: Python 3.13.2
- PixelRAG: 0.4.0
- Retrieval backend: hosted PixelRAG API
- Local PixelRAG index: intentionally not used because of its approximately 217 GB size
- Evaluation split: frozen 150 images, 30 countries × 5 images, seed 42
- Primary target: country-level evidence

## Phase 1 — Environment and API verification

Status: COMPLETE

Verified:

- Python virtual environment
- PixelRAG installation/import
- PixelRAG CLI availability
- Hosted API connectivity
- Text query endpoint
- Image query endpoint

The image-query smoke test returned five visual retrieval hits, confirming that the hosted image retrieval path worked before the benchmark run.

## Phase 2 — Dataset and frozen evaluation set

Status: COMPLETE

Source dataset: `ubitquitin/geolocation-geoguessr-images-50k`

- 49,997 unique image files identified
- 124 countries represented
- 104 countries with at least five images
- Frozen sample: 30 countries × 5 images = 150 images
- Sampling seed: 42
- Selected metadata saved to `data/eval_metadata.csv`
- Sampling plan saved to `data/sample_plan.csv`
- 150/150 selected images downloaded successfully

The frozen split was not changed during later experiments.

## Phase 3 — Image-only PixelRAG retrieval baseline

Status: COMPLETE

Configuration:

- Image query
- Top-k = 5
- Hosted PixelRAG API
- 150 benchmark images

Outputs:

- `results/retrieval_records.jsonl`
- `results/retrieval_hits.csv`

Final retrieval output contains 150 unique image records and 750 Top-5 retrieval hits.

## Phase 4 — Baseline evaluation

Status: COMPLETE

Primary metric: strict country evidence in retrieved page titles.

The initial evaluation artifact reported 27/150 images with correct country evidence. A later stricter comparable evaluation path used in Phase 6 reported 26/150. Both artifacts are preserved; the final report uses the Phase 6 protocol for the main baseline/reader comparison and explicitly documents the discrepancy.

## Phase 5 — Deterministic reader

Status: COMPLETE

Reader:

- Rank-weighted country-title reader
- Rank weights: 1=5, 2=4, 3=3, 4=2, 5=1
- Gold country is not used during prediction
- UNKNOWN when no explicit country evidence is available or when scores tie

Outputs:

- `results/reader_predictions.csv`
- `results/reader_metrics.json`

Final reader metrics:

- Correct: 26/150
- Incorrect: 25/150
- UNKNOWN: 99/150
- Coverage: 34.0%
- Overall accuracy: 17.3%
- Selective accuracy: 51.0%

## Phase 6 — Quantitative comparison

Status: COMPLETE

Final comparison:

- Correct Top-5 country evidence: 26/150 (17.3%)
- Correct evidence → correct reader: 26/26
- Correct evidence → wrong reader: 0/26
- Correct evidence → UNKNOWN: 0/26
- No correct evidence → correct reader: 0/124
- No correct evidence → wrong reader: 25/124
- No correct evidence → UNKNOWN: 99/124

This result identifies retrieval quality as the main bottleneck for the simple deterministic reader pipeline.

## Phase 7 — Failure analysis

Status: COMPLETE

The automated preliminary taxonomy was applied to the 124 images without correct Top-5 country evidence.

Largest categories:

- Generic retrieval: 42 (33.9%)
- Weak/non-specific retrieval: 32 (25.8%)
- Wrong-country transport/road: 20 (16.1%)
- Landmark/location bias: 13 (10.5%)

Additional categories are retained in `results/phase7_failure_summary.json` and `results/phase7_failure_analysis.csv`.

Forty-five cases were flagged for manual review. Manual review was left as an optional refinement and was not presented as completed human annotation.

## Phase 8 — OCR/text-aware extension

Status: COMPLETE

Pipeline:

- EasyOCR
- Central gameplay crop
- OCR confidence threshold
- UI phrase filtering
- Garbage/noise filtering
- PixelRAG text query only when useful text remained

All 150 images were processed.

Results:

- Useful OCR text: 3/150 (2.0%)
- No useful OCR text: 147/150 (98.0%)

Successful OCR cases:

- `geo_0055` — France: `liledeFrance moblites`, `Hybride`
- `geo_0111` — South Korea: `KOREA`, `coffee`
- `geo_0133` — Uganda: `REAL TASK`

## Phase 9 — Text-aware versus image-only comparison

Status: COMPLETE

Among the three successful OCR cases:

- Image-only correct evidence: 0/3
- Text-aware correct evidence: 1/3
- Text-added correct evidence: 1/3
- Neither correct: 2/3

The France case produced correct France-specific evidence at rank 3 through text-aware retrieval, where image-only retrieval had no correct France evidence.

The South Korea case remained unresolved under strict matching because `KOREA` was not sufficient to distinguish South Korea from North Korea-related retrieval.

The Uganda case produced non-geographic OCR text (`REAL TASK`) and remained unresolved.

## Final research interpretation

The experiment supports three defensible conclusions:

1. PixelRAG visual retrieval can surface useful geographic evidence, but correct country evidence was sparse: 26/150 (17.3%) under the finalized Phase 6 protocol.
2. When explicit correct country evidence was present, the deterministic reader converted it correctly in all 26 cases; retrieval was therefore the main bottleneck in this simple pipeline.
3. Text-aware retrieval can add useful evidence in at least one observed case, but the current OCR pipeline produced usable text for only 3/150 images (2.0%), so the 1/3 result is a proof of concept rather than an overall accuracy improvement estimate.

## Final artifacts

- `results/phase6_metrics.json`
- `results/phase6_image_analysis.csv`
- `results/phase7_failure_analysis.csv`
- `results/phase7_failure_summary.json`
- `results/text_aware_records.jsonl`
- `results/phase9_text_vs_image.csv`
- `results/phase9_metrics.json`
- `report/PixelRAG_GeoGuessr_Research_Report.pdf`
