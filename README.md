# PixelRAG for GeoGuessr

Research tryout project evaluating **PixelRAG-style visual retrieval for GeoGuessr-style image geolocation**, with a small OCR/text-aware extension.

## Research question

> How useful is PixelRAG-style visual retrieval for image geolocation, and which kinds of visual evidence make retrieval succeed or fail on GeoGuessr-style images?

## Final results

The experiment uses a **frozen 150-image benchmark**: 30 countries × 5 images, selected with random seed 42.

### Image-only baseline

- PixelRAG Top-5 correct country evidence: **26/150 (17.3%)**
- Deterministic reader coverage: **51/150 (34.0%)**
- Reader correct: **26/150 (17.3%)**
- Reader incorrect: **25/150 (16.7%)**
- Reader `UNKNOWN`: **99/150 (66.0%)**
- Selective accuracy: **51.0%**

When correct country evidence was present in the Top-5, the deterministic reader converted it correctly in all 26 cases. When correct evidence was absent, the reader produced 25 incorrect predictions and 99 abstentions.

### Text-aware extension

A conservative EasyOCR → PixelRAG text pipeline processed all 150 images.

- Useful OCR text: **3/150 (2.0%)**
- No useful OCR text: **147/150 (98.0%)**
- Text-aware correct evidence among OCR-success cases: **1/3 (33.3%)**
- Text-added correct evidence: **1/3**

The France case (`geo_0055`) is the clearest proof of concept: OCR produced `liledeFrance moblites | Hybride`, and text-aware retrieval recovered France-specific evidence that was absent from image-only Top-5 retrieval.

The 1/3 text-aware result is **not** interpreted as an overall accuracy improvement because OCR coverage was only 2% and the comparison contains only three cases.

## Dataset

Source dataset: `ubitquitin/geolocation-geoguessr-images-50k`

The project enumerated **49,997 unique image files across 124 countries** and froze a 150-image evaluation subset. Country-level evaluation is used because reliable city/region labels were not available in the frozen metadata.

The selected images are recorded in:

- `data/sample_plan.csv`
- `data/eval_metadata.csv`

The repository does **not** require the approximately 217 GB local PixelRAG index. The completed retrieval baseline uses the hosted PixelRAG API.

## Repository structure

```text
.
├── README.md
├── requirements.txt
├── configs/
│   └── baseline.yaml
├── data/
│   ├── README.md
│   ├── eval_metadata.csv
│   ├── sample_plan.csv
│   └── kaggle_file_manifest.csv
├── src/
│   ├── prepare_dataset.py
│   ├── query_pixelrag.py
│   ├── evaluate.py
│   ├── run_reader.py
│   ├── evaluate_reader.py
│   ├── analyze_phase6.py
│   ├── analyze_phase7.py
│   ├── prepare_manual_review.py
│   ├── evaluate_phase9.py
│   ├── analyze_failures.py
│   └── text_aware.py
├── results/
│   ├── retrieval_records.jsonl
│   ├── retrieval_hits.csv
│   ├── phase6_metrics.json
│   ├── phase7_failure_analysis.csv
│   ├── phase7_failure_summary.json
│   ├── text_aware_records.jsonl
│   ├── phase9_text_vs_image.csv
│   ├── phase9_metrics.json
│   └── ...
├── report/
│   └── PixelRAG_GeoGuessr_Research_Report.pdf
└── experiments/
    └── EXPERIMENT_LOG.md
```

## Reproduce the pipeline

Create the environment and install dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Prepare the frozen evaluation set:

```powershell
python src\prepare_dataset.py --plan
python src\prepare_dataset.py --download
```

Run the hosted PixelRAG image baseline:

```powershell
python src\query_pixelrag.py --limit 150
```

Evaluate retrieval and reader stages:

```powershell
python src\evaluate.py
python src\run_reader.py
python src\evaluate_reader.py
python src\analyze_phase6.py
python src\analyze_phase7.py
```

Run the OCR/text-aware extension and comparison:

```powershell
python src\text_aware.py --limit 150
python src\evaluate_phase9.py
```

The stored result files allow inspection without re-running the API queries.

## Evaluation discipline

- The 150-image split is frozen.
- Gold country labels are used for evaluation, not for PixelRAG querying.
- Country matching uses strict aliases to reduce false positives.
- The deterministic reader does not use gold labels during prediction.
- Raw retrieval outputs are preserved.
- Failure categories are explicitly described as preliminary automated labels, not human-validated visual annotations.
- Weak or negative results are reported rather than replaced with stronger-looking qualitative examples.

## Important metric note

An earlier Phase 4 artifact reports **27/150** images with any correct country evidence. The finalized Phase 6 comparison uses a stricter comparable matching path and reports **26/150**. The research report documents this discrepancy and uses the Phase 6 result for the main baseline/reader comparison.

## Report

The submission-ready report is available at:

`report/PixelRAG_GeoGuessr_Research_Report.pdf`

## Main result files

- `results/retrieval_records.jsonl` — raw PixelRAG responses
- `results/retrieval_hits.csv` — flattened Top-5 retrievals
- `results/phase6_metrics.json` — finalized baseline/reader comparison
- `results/reader_predictions.csv` — deterministic reader outputs
- `results/phase7_failure_analysis.csv` — preliminary failure categories
- `results/text_aware_records.jsonl` — OCR/text retrieval records
- `results/phase9_text_vs_image.csv` — image-only vs text-aware comparison
- `results/phase9_metrics.json` — Phase 9 summary

## Scope and limitations

This is a focused research tryout, not a complete GeoGuessr solver. The primary metric measures explicit country evidence in retrieved page titles rather than end-to-end geolocation accuracy. The OCR extension has very low coverage, and its 1/3 text-added result is a proof-of-concept observation rather than a statistically stable improvement estimate.
