"""Analyze PixelRAG retrieval failure patterns."""

import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

HITS = ROOT / "results" / "retrieval_hits.csv"
PRED = ROOT / "results" / "baseline_predictions.csv"
OUT = ROOT / "results" / "failure_analysis.csv"


with PRED.open(encoding="utf-8", newline="") as f:
    predictions = {
        row["image_id"]: row
        for row in csv.DictReader(f)
    }


hits_by_image = {}

with HITS.open(encoding="utf-8", newline="") as f:
    for row in csv.DictReader(f):
        hits_by_image.setdefault(row["image_id"], []).append(row)


rows = []

for image_id, prediction in predictions.items():

    hits = sorted(
        hits_by_image.get(image_id, []),
        key=lambda row: int(row["rank"]),
    )

    titles = [hit["title"] for hit in hits]
    combined_titles = " ".join(titles).lower()

    if prediction["country_evidence_top5"].lower() == "true":
        category = "explicit_country_evidence"

    elif any(
        term in combined_titles
        for term in [
            "street_view",
            "geoguessr",
            "google_maps",
        ]
    ):
        category = "generic_streetview_or_mapping"

    elif any(
        term in combined_titles
        for term in [
            "road",
            "highway",
            "route",
            "street",
            "road_sign",
        ]
    ):
        category = "transport_or_road_evidence"

    elif any(
        term in combined_titles
        for term in [
            "geography",
            "city",
            "monument",
            "house",
            "building",
            "park",
        ]
    ):
        category = "location_related_visual_evidence"

    else:
        category = "weak_or_non_specific_retrieval"

    rows.append(
        {
            "image_id": image_id,
            "country": prediction["country"],
            "category": category,
            "top1_title": titles[0] if titles else "",
            "top5_titles": " || ".join(titles),
        }
    )


with OUT.open("w", encoding="utf-8", newline="") as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "image_id",
            "country",
            "category",
            "top1_title",
            "top5_titles",
        ],
    )

    writer.writeheader()
    writer.writerows(rows)


counts = Counter(row["category"] for row in rows)

print("Failure analysis complete.")
print("Images:", len(rows))
print()

for category, count in counts.most_common():
    print(
        f"{category}: "
        f"{count} "
        f"({count / len(rows):.1%})"
    )

print()
print("Saved:", OUT)