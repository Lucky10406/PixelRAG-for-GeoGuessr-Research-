# Data

The evaluation uses the Kaggle dataset `ubitquitin/geolocation-geoguessr-images-50k`.

The repository stores only the frozen metadata and sampling artifacts needed to reproduce the evaluation definition:

- `sample_plan.csv` — frozen 30-country × 5-image sampling plan, seed 42
- `eval_metadata.csv` — selected image metadata
- `kaggle_file_manifest.csv` — enumerated dataset file manifest

Raw image files are intentionally not committed to GitHub. Download the source dataset separately and run:

```powershell
python src\prepare_dataset.py --plan
python src\prepare_dataset.py --download
```
