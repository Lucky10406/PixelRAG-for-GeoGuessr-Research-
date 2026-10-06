"""Evaluate PixelRAG retrieval evidence for the frozen GeoGuessr sample.

This evaluates whether retrieved Wikipedia page titles contain explicit
evidence for the gold country. It is a retrieval-evidence metric, not
an end-to-end geolocation accuracy metric.
"""

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

METADATA = ROOT / "data" / "eval_metadata.csv"
HITS = ROOT / "results" / "retrieval_hits.csv"
PREDICTIONS = ROOT / "results" / "baseline_predictions.csv"
METRICS = ROOT / "results" / "metrics.json"


COUNTRY_ALIASES = {
    "Andorra": ["andorra"],
    "Argentina": ["argentina"],
    "Botswana": ["botswana"],
    "Bulgaria": ["bulgaria"],
    "Cambodia": ["cambodia", "khmer"],
    "China": ["china", "chinese"],
    "Ecuador": ["ecuador"],
    "Estonia": ["estonia", "estonian"],
    "Eswatini": ["eswatini", "swaziland"],
    "Faroe Islands": ["faroe islands", "faroe"],
    "France": ["france", "french"],
    "Greenland": ["greenland"],
    "Latvia": ["latvia", "latvian"],
    "Lebanon": ["lebanon", "lebanese"],
    "Luxembourg": ["luxembourg"],
    "Montenegro": ["montenegro"],
    "Northern Mariana Islands": [
        "northern mariana islands",
        "northern mariana",
    ],
    "Pakistan": ["pakistan", "pakistani"],
    "Poland": ["poland", "polish"],
    "Puerto Rico": ["puerto rico"],
    "Senegal": ["senegal", "senegalese"],
    "South Africa": ["south africa", "south african"],
    "South Korea": [
        "south korea",
        "republic of korea",
        "south_korea",
        "republic_of_korea",
    ],
    "Switzerland": ["switzerland", "swiss"],
    "Taiwan": ["taiwan"],
    "Tunisia": ["tunisia", "tunisian"],
    "Uganda": ["uganda", "ugandan"],
    "United Arab Emirates": [
        "united arab emirates",
        "united_arab_emirates",
        "uae",
    ],
    "United Kingdom": [
        "united kingdom",
        "united_kingdom",
        "great britain",
        "great_britain",
    ],
    "United States": [
        "united states",
        "united_states",
        "united states of america",
        "united_states_of_america",
        "u.s.",
        "u.s",
        "usa",
    ],
}


def normalize(text):
    """Normalize Wikipedia-style titles for matching."""
    return (
        str(text or "")
        .lower()
        .replace("_", " ")
        .replace("-", " ")
    )


def title_matches_country(title, country):
    """Return True only for country-specific aliases.

    Important: broad aliases such as 'korea' or 'america' are intentionally
    excluded because they create false positives.
    """
    text = normalize(title)

    aliases = COUNTRY_ALIASES.get(country, [])

    return any(
        alias.lower().replace("_", " ") in text
        for alias in aliases
    )


def main():

    metadata = {}

    with METADATA.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            metadata[row["image_id"]] = row

    hits_by_image = {}

    with HITS.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            hits_by_image.setdefault(
                row["image_id"],
                []
            ).append(row)

    predictions = []

    for image_id, meta in metadata.items():

        country = meta["country"]

        hits = sorted(
            hits_by_image.get(image_id, []),
            key=lambda row: int(row["rank"]),
        )

        matching = [
            hit
            for hit in hits
            if title_matches_country(
                hit["title"],
                country,
            )
        ]

        first_match = matching[0] if matching else None

        predictions.append(
            {
                "image_id": image_id,
                "country": country,
                "top1_title": (
                    hits[0]["title"]
                    if hits
                    else ""
                ),
                "top1_score": (
                    hits[0]["score"]
                    if hits
                    else ""
                ),
                "country_evidence_top1": bool(
                    first_match
                    and int(first_match["rank"]) == 1
                ),
                "country_evidence_top5": bool(
                    first_match
                ),
                "first_evidence_rank": (
                    int(first_match["rank"])
                    if first_match
                    else ""
                ),
                "first_evidence_score": (
                    first_match["score"]
                    if first_match
                    else ""
                ),
            }
        )

    total = len(predictions)

    top1 = sum(
        p["country_evidence_top1"]
        for p in predictions
    )

    top5 = sum(
        p["country_evidence_top5"]
        for p in predictions
    )

    rank_values = [
        p["first_evidence_rank"]
        for p in predictions
        if p["first_evidence_rank"] != ""
    ]

    metrics = {
        "experiment": "baseline-v0",
        "evaluation_type": "retrieval_country_evidence",
        "n_images": total,
        "top1_country_evidence_rate": (
            top1 / total
            if total
            else 0
        ),
        "top5_country_evidence_rate": (
            top5 / total
            if total
            else 0
        ),
        "images_with_any_country_evidence": len(
            rank_values
        ),
        "images_without_country_evidence": (
            total - len(rank_values)
        ),
        "mean_first_evidence_rank": (
            sum(rank_values) / len(rank_values)
            if rank_values
            else None
        ),
        "frozen_split": True,
        "retrieval_top_k": 5,
        "text_annotation_available": False,
        "country_matching_version": "v2_strict",
        "note": (
            "Metrics measure explicit country-specific evidence "
            "in retrieved page titles. They are not end-to-end "
            "geolocation accuracy."
        ),
    }

    with PREDICTIONS.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=predictions[0].keys(),
        )

        writer.writeheader()
        writer.writerows(predictions)

    with METRICS.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            metrics,
            f,
            indent=2,
        )

    print("Strict country matching evaluation complete.")
    print("Images evaluated:", total)
    print(
        f"Top-1 country evidence: "
        f"{top1}/{total} = "
        f"{metrics['top1_country_evidence_rate']:.3f}"
    )
    print(
        f"Top-5 country evidence: "
        f"{top5}/{total} = "
        f"{metrics['top5_country_evidence_rate']:.3f}"
    )
    print(
        "Images with any country evidence:",
        len(rank_values),
        f"/{total}",
    )
    print(
        "Images without country evidence:",
        total - len(rank_values),
        f"/{total}",
    )
    print(
        "Mean first evidence rank:",
        metrics["mean_first_evidence_rank"],
    )
    print()
    print("Saved:", PREDICTIONS)
    print("Saved:", METRICS)


if __name__ == "__main__":
    main()