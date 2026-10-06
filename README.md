# PixelRAG for GeoGuessr

Research tryout project exploring how useful PixelRAG-style visual retrieval is for image geolocation on GeoGuessr-style images.

## Current status

**Phase 1 — Environment and API verification: COMPLETE**

- Python 3.13.2 virtual environment
- PixelRAG 0.4.0 installed
- Hosted PixelRAG API verified
- Text search endpoint verified
- Image retrieval endpoint verified

**Phase 2 — Dataset and frozen evaluation split: COMPLETE**

- Dataset: `ubitquitin/geolocation-geoguessr-images-50k`
- 49,997 unique image files identified
- 124 countries represented
- Frozen evaluation split: **150 images**
- 30 countries × 5 images
- Random seed: 42
- Country-level evaluation is the primary task because the dataset metadata does not provide reliable city/region labels.

**Phase 3 — PixelRAG visual retrieval baseline: COMPLETE**

- 150 frozen GeoGuessr images queried
- Top-k = 5
- **750 retrieval hits saved**
- Raw retrieval responses saved to `results/retrieval_records.jsonl`
- Flattened retrieval results saved to `results/retrieval_hits.csv`
- Initial smoke-test duplicate removed
- No additional API queries are required for this completed retrieval baseline

**Phase 4 — Evaluation: NEXT**

The next stage will evaluate how often retrieved visual evidence provides useful country-level geographic evidence.

## Phase tracking

- [x] Phase 0 — Research definition
- [x] Phase 1 — Environment + PixelRAG smoke test
- [x] Phase 2 — Dataset acquisition + frozen evaluation set
- [x] Phase 3 — PixelRAG visual retrieval baseline
- [x] Phase 4 — Evaluation
- [x] Phase 5 — Reader / location reasoning
- [x] Phase 6 — Quantitative evaluation
- [x] Phase 7 — Failure analysis
- [x] Phase 8 — Text-aware extension
- [x] Phase 9 — Extension evaluation
- [x] Phase 10 — Final analysis and figures
- [ ] Phase 11 — Research report
- [ ] Phase 12 — Reproducibility + GitHub cleanup
- [ ] Phase 13 — Final QA + submission

## Research question

> How useful is PixelRAG-style visual retrieval for image geolocation, and which kinds of visual evidence make retrieval succeed or fail on GeoGuessr-style images?

A later extension will investigate whether visible text can be extracted and used to make retrieval more targeted.

## Project structure

```text
pixelrag-geoguessr-tryout/
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
│   ├── run_reader.py
│   ├── evaluate.py
│   ├── analyze_failures.py
│   └── text_aware.py
├── results/
│   ├── README.md
│   ├── retrieval_records.jsonl
│   └── retrieval_hits.csv
├── figures/
├── report/
└── experiments/
    └── EXPERIMENT_LOG.md
```


Running the project

Create and activate the virtual environment, then install:

pip install -r requirements.txt

The dataset preparation script can enumerate the Kaggle dataset, freeze the evaluation sample, and download the selected images.

The PixelRAG retrieval baseline can be run with:

python src/query_pixelrag.py --limit 150

The completed Phase 3 retrieval artifacts are already stored in results/, so the baseline does not need to be rerun to continue with evaluation.

Dataset

Source dataset:

ubitquitin/geolocation-geoguessr-images-50k

The dataset contains GeoGuessr-style images organized by country. The project uses a frozen subset rather than the full dataset to keep the tryout reproducible and computationally manageable.

Evaluation plan

The evaluation will measure:

country-level prediction accuracy
retrieval evidence hits in top-k
rank of the first useful geographic evidence
score of useful retrieved evidence
text-rich vs. text-poor retrieval behavior where metadata supports it
qualitative retrieval successes and failures

No ground-truth information is used in the PixelRAG query itself.

Research discipline

This repository keeps retrieval outputs separate from later evaluation and reasoning stages.

Important constraints:

Do not use the 217 GB local PixelRAG index as a dependency.
Do not manually edit predictions.
Do not cherry-pick qualitative examples as quantitative evidence.
Keep the 150-image evaluation split frozen.
Record failed experiments and implementation decisions.
Report negative or weak results honestly.
Current checkpoint

Phase 3 complete — 4 October 2026

The project has progressed from environment setup to a reproducible 150-image hosted PixelRAG visual retrieval baseline.

Next milestone: implement and run Phase 4 evaluation.
