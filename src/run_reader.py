"""
Phase 5: Deterministic retrieval reader.

Reads PixelRAG Top-5 retrieval results and converts explicit
country mentions in retrieved titles into a country prediction.

Important:
- The gold country is NOT used during prediction.
- The reader only uses retrieval_hits.csv.
- UNKNOWN is allowed when there is no explicit country evidence.
"""

from pathlib import Path
import csv
import json
import re
from collections import defaultdict


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = PROJECT_ROOT / "results" / "retrieval_hits.csv"
OUTPUT_FILE = PROJECT_ROOT / "results" / "reader_predictions.csv"


# Fixed country vocabulary for the frozen 30-country benchmark.
# These aliases are intentionally strict to reduce false positives.
COUNTRY_ALIASES = {
    "Andorra": [
        "andorra",
    ],
    "Argentina": [
        "argentina",
    ],
    "Botswana": [
        "botswana",
    ],
    "Bulgaria": [
        "bulgaria",
    ],
    "Cambodia": [
        "cambodia",
    ],
    "China": [
        "china",
    ],
    "Ecuador": [
        "ecuador",
    ],
    "Estonia": [
        "estonia",
    ],
    "Eswatini": [
        "eswatini",
        "swaziland",
    ],
    "Faroe Islands": [
        "faroe islands",
        "faroe_islands",
    ],
    "France": [
        "france",
    ],
    "Greenland": [
        "greenland",
    ],
    "Latvia": [
        "latvia",
    ],
    "Lebanon": [
        "lebanon",
    ],
    "Luxembourg": [
        "luxembourg",
    ],
    "Montenegro": [
        "montenegro",
    ],
    "Northern Mariana Islands": [
        "northern mariana islands",
        "northern_mariana_islands",
    ],
    "Pakistan": [
        "pakistan",
    ],
    "Poland": [
        "poland",
    ],
    "Puerto Rico": [
        "puerto rico",
        "puerto_rico",
    ],
    "Senegal": [
        "senegal",
    ],
    "South Africa": [
        "south africa",
        "south_africa",
    ],
    "South Korea": [
        "south korea",
        "south_korea",
        "republic of korea",
        "republic_of_korea",
    ],
    "Switzerland": [
        "switzerland",
    ],
    "Taiwan": [
        "taiwan",
    ],
    "Tunisia": [
        "tunisia",
    ],
    "Uganda": [
        "uganda",
    ],
    "United Arab Emirates": [
        "united arab emirates",
        "united_arab_emirates",
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


# Higher-ranked retrievals receive more evidence weight.
RANK_WEIGHTS = {
    1: 5.0,
    2: 4.0,
    3: 3.0,
    4: 2.0,
    5: 1.0,
}


def normalize(text):
    """Normalize title text for alias matching."""
    text = str(text).lower()
    text = text.replace("_", " ")
    text = text.replace("-", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def find_country_candidates(title):
    """
    Return countries explicitly mentioned in a retrieved title.
    """
    normalized_title = normalize(title)

    matches = []

    for country, aliases in COUNTRY_ALIASES.items():
        for alias in aliases:
            normalized_alias = normalize(alias)

            if normalized_alias in normalized_title:
                matches.append(country)
                break

    return matches


def load_retrieval_hits():
    """Load retrieval hits grouped by image."""
    grouped = defaultdict(list)

    with INPUT_FILE.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            image_id = row["image_id"]

            try:
                rank = int(row["rank"])
            except (ValueError, TypeError):
                continue

            if rank > 5:
                continue

            try:
                score = float(row["score"])
            except (ValueError, TypeError):
                score = 0.0

            grouped[image_id].append(
                {
                    "rank": rank,
                    "score": score,
                    "title": row["title"],
                    "article_id": row["article_id"],
                }
            )

    # Sort every image's hits by retrieval rank.
    for image_id in grouped:
        grouped[image_id].sort(key=lambda x: x["rank"])

    return grouped


def predict_for_image(hits):
    """
    Convert Top-5 retrieved titles into a country prediction.

    Returns:
        prediction,
        confidence,
        evidence_rank,
        evidence_score,
        evidence_title,
        candidate_scores,
        status
    """

    candidate_scores = defaultdict(float)
    candidate_evidence = defaultdict(list)

    for hit in hits:
        rank = hit["rank"]

        if rank not in RANK_WEIGHTS:
            continue

        countries = find_country_candidates(hit["title"])

        for country in countries:
            weight = RANK_WEIGHTS[rank]

            candidate_scores[country] += weight

            candidate_evidence[country].append(
                {
                    "rank": rank,
                    "score": hit["score"],
                    "title": hit["title"],
                    "weight": weight,
                }
            )

    # No explicit country evidence.
    if not candidate_scores:
        return (
            "UNKNOWN",
            0.0,
            "",
            "",
            "",
            {},
            "no_explicit_country_evidence",
        )

    # Sort candidates by accumulated evidence score.
    ranked_candidates = sorted(
        candidate_scores.items(),
        key=lambda x: (-x[1], x[0]),
    )

    best_country, best_value = ranked_candidates[0]

    # If two or more candidates have the same score, abstain.
    tied = [
        country
        for country, value in ranked_candidates
        if value == best_value
    ]

    if len(tied) > 1:
        return (
            "UNKNOWN",
            0.0,
            "",
            "",
            "",
            dict(ranked_candidates),
            "tie",
        )

    evidence = sorted(
        candidate_evidence[best_country],
        key=lambda x: x["rank"],
    )

    first_evidence = evidence[0]

    total_score = sum(candidate_scores.values())

    if total_score > 0:
        confidence = best_value / total_score
    else:
        confidence = 0.0

    return (
        best_country,
        confidence,
        first_evidence["rank"],
        first_evidence["score"],
        first_evidence["title"],
        dict(ranked_candidates),
        "explicit_match",
    )


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    grouped = load_retrieval_hits()

    print(f"Images with retrieval results: {len(grouped)}")

    rows = []

    for image_id in sorted(grouped.keys()):
        hits = grouped[image_id]

        (
            predicted_country,
            confidence,
            evidence_rank,
            evidence_score,
            evidence_title,
            candidate_scores,
            status,
        ) = predict_for_image(hits)

        rows.append(
            {
                "image_id": image_id,
                "predicted_country": predicted_country,
                "confidence": round(confidence, 6),
                "evidence_rank": evidence_rank,
                "evidence_score": evidence_score,
                "evidence_title": evidence_title,
                "candidate_countries": json.dumps(
                    candidate_scores,
                    ensure_ascii=False,
                ),
                "reader_status": status,
            }
        )

    fieldnames = [
        "image_id",
        "predicted_country",
        "confidence",
        "evidence_rank",
        "evidence_score",
        "evidence_title",
        "candidate_countries",
        "reader_status",
    ]

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)

    prediction_count = sum(
        row["predicted_country"] != "UNKNOWN"
        for row in rows
    )

    unknown_count = len(rows) - prediction_count

    print()
    print("Phase 5 reader complete.")
    print(f"Images processed: {len(rows)}")
    print(f"Country predictions: {prediction_count}")
    print(f"UNKNOWN / abstained: {unknown_count}")
    print()
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()