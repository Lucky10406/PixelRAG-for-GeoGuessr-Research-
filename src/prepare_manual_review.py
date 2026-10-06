import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

analysis_path = ROOT / "results" / "phase7_failure_analysis.csv"
metadata_path = ROOT / "data" / "eval_metadata.csv"
hits_path = ROOT / "results" / "retrieval_hits.csv"

analysis = pd.read_csv(analysis_path)
metadata = pd.read_csv(metadata_path)
hits = pd.read_csv(hits_path)

print("Phase 7 analysis columns:")
print(list(analysis.columns))

# Use the manual-review flag produced by the Phase 7 analysis.
flagged = analysis[
    analysis["manual_review_needed"].astype(str).str.lower().isin(
        ["true", "1", "yes"]
    )
].copy()

print(f"Flagged cases found: {len(flagged)}")

rows = []

for _, row in flagged.iterrows():
    image_id = row["image_id"]

    meta = metadata[metadata["image_id"] == image_id]

    if meta.empty:
        continue

    meta_row = meta.iloc[0]

    image_hits = hits[
        hits["image_id"] == image_id
    ].sort_values("rank")

    hit_values = []

    for _, hit in image_hits.iterrows():
        hit_values.append(
            (
                str(hit["title"]),
                round(float(hit["score"]), 4)
            )
        )

    while len(hit_values) < 5:
        hit_values.append(("", ""))

    rows.append({
        "image_id": image_id,
        "image_path": meta_row["image_path"],
        "gold_country": meta_row["country"],

        "auto_retrieval_failure_type": row["retrieval_failure_type"],
        "auto_retrieval_reason": row["retrieval_reason"],
        "auto_reader_failure_type": row["reader_failure_type"],

        "rank1_title": hit_values[0][0],
        "rank1_score": hit_values[0][1],
        "rank2_title": hit_values[1][0],
        "rank2_score": hit_values[1][1],
        "rank3_title": hit_values[2][0],
        "rank3_score": hit_values[2][1],
        "rank4_title": hit_values[3][0],
        "rank4_score": hit_values[3][1],
        "rank5_title": hit_values[4][0],
        "rank5_score": hit_values[4][1],

        "manual_failure_type": "",
        "manual_evidence": "",
        "manual_notes": ""
    })

output = pd.DataFrame(rows)

output_path = ROOT / "results" / "phase7_manual_review.csv"
output.to_csv(output_path, index=False)

print()
print("Manual review file created.")
print(f"Flagged cases: {len(output)}")
print(f"Saved: {output_path}")