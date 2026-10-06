# Results

This directory contains machine-readable outputs from the completed experiments.

Key files:

- `retrieval_records.jsonl` — raw hosted PixelRAG responses for the 150-image baseline
- `retrieval_hits.csv` — flattened Top-5 retrieval records
- `baseline_predictions.csv` — baseline evaluation output
- `metrics.json` — Phase 4 evaluation artifact
- `reader_predictions.csv` / `reader_metrics.json` — deterministic reader outputs
- `phase6_image_analysis.csv` / `phase6_metrics.json` — finalized quantitative comparison
- `phase7_failure_analysis.csv` / `phase7_failure_summary.json` — preliminary failure analysis
- `phase7_manual_review.csv` — flagged manual-review cases
- `text_aware_records.jsonl` — OCR/text-aware retrieval outputs
- `phase9_text_vs_image.csv` / `phase9_metrics.json` — text-aware vs image-only comparison

The main report uses the finalized Phase 6 and Phase 9 outputs. The earlier 27/150 Phase 4 metric is preserved as an artifact and explicitly documented as a matching-protocol discrepancy.
