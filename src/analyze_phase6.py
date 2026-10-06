"""
Phase 6: Quantitative comparison of retrieval evidence and reader outcomes.

This analysis joins:
1. Frozen gold labels
2. PixelRAG Top-5 retrieval evidence
3. Phase 5 reader predictions

It measures whether correct retrieval evidence was available and
whether the reader converted that evidence into a correct prediction.
"""

from pathlib import Path
import csv
import json
import re
from collections import Counter, defaultdict


PROJECT_ROOT = Path(__file__).resolve().parents[1]

METADATA_FILE = PROJECT_ROOT / "data" / "eval_metadata.csv"
RETRIEVAL_FILE = PROJECT_ROOT / "results" / "retrieval_hits.csv"
READER_FILE = PROJECT_ROOT / "results" / "reader_predictions.csv"

IMAGE_OUTPUT = PROJECT_ROOT / "results" / "phase6_image_analysis.csv"
METRICS_OUTPUT = PROJECT_ROOT / "results" / "phase6_metrics.json"


# Same strict country aliases used for the Phase 4/5 benchmark.
COUNTRY_ALIASES = {
    "Andorra": ["andorra"],
    "Argentina": ["argentina"],
    "Botswana": ["botswana"],
    "Bulgaria": ["bulgaria"],
    "Cambodia": ["cambodia"],
    "China": ["china"],
    "Ecuador": ["ecuador"],
    "Estonia": ["estonia"],
    "Eswatini": ["eswatini", "swaziland"],
    "Faroe Islands": ["faroe islands", "faroe_islands"],
    "France": ["france"],
    "Greenland": ["greenland"],
    "Latvia": ["latvia"],
    "Lebanon": ["lebanon"],
    "Luxembourg": ["luxembourg"],
    "Montenegro": ["montenegro"],
    "Northern Mariana Islands": [
        "northern mariana islands",
        "northern_mariana_islands",
    ],
    "Pakistan": ["pakistan"],
    "Poland": ["poland"],
    "Puerto Rico": ["puerto rico", "puerto_rico"],
    "Senegal": ["senegal"],
    "South Africa": ["south africa", "south_africa"],
    "South Korea": [
        "south korea",
        "south_korea",
        "republic of korea",
        "republic_of_korea",
    ],
    "Switzerland": ["switzerland"],
    "Taiwan": ["taiwan"],
    "Tunisia": ["tunisia"],
    "Uganda": ["uganda"],
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


def normalize(text):
    text = str(text).lower()
    text = text.replace("_", " ")
    text = text.replace("-", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def find_country_mentions(title):
    """
    Return all benchmark countries explicitly mentioned in a title.
    """
    normalized = normalize(title)

    matches = []

    for country, aliases in COUNTRY_ALIASES.items():
        for alias in aliases:
            if normalize(alias) in normalized:
                matches.append(country)
                break

    return matches


def load_metadata():
    gold = {}

    with METADATA_FILE.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as f:
        reader = csv.DictReader(f)

        for row in reader:
            gold[row["image_id"]] = row["country"]

    return gold


def load_retrieval():
    """
    Load Top-5 retrieval results for each image.
    """
    retrieval = defaultdict(list)

    with RETRIEVAL_FILE.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as f:
        reader = csv.DictReader(f)

        for row in reader:
            image_id = row["image_id"]

            try:
                rank = int(row["rank"])
            except (ValueError, TypeError):
                continue

            if rank > 5:
                continue

            retrieval[image_id].append(
                {
                    "rank": rank,
                    "score": row["score"],
                    "title": row["title"],
                    "article_id": row["article_id"],
                }
            )

    for image_id in retrieval:
        retrieval[image_id].sort(
            key=lambda x: x["rank"]
        )

    return retrieval


def load_reader():
    reader_results = {}

    with READER_FILE.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as f:
        reader = csv.DictReader(f)

        for row in reader:
            reader_results[row["image_id"]] = row

    return reader_results


def safe_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def safe_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def main():
    gold = load_metadata()
    retrieval = load_retrieval()
    reader_results = load_reader()

    image_rows = []

    for image_id in sorted(gold.keys()):
        gold_country = gold[image_id]

        if image_id not in reader_results:
            raise ValueError(
                f"Missing Phase 5 reader result: {image_id}"
            )

        reader = reader_results[image_id]

        predicted_country = reader["predicted_country"]
        reader_status = reader["reader_status"]

        if predicted_country == "UNKNOWN":
            reader_outcome = "UNKNOWN"
        elif predicted_country == gold_country:
            reader_outcome = "CORRECT"
        else:
            reader_outcome = "INCORRECT"

        hits = retrieval.get(image_id, [])

        correct_evidence = []
        all_country_evidence = []

        for hit in hits:
            mentioned = find_country_mentions(
                hit["title"]
            )

            for country in mentioned:
                evidence_record = {
                    "country": country,
                    "rank": hit["rank"],
                    "score": safe_float(hit["score"]),
                    "title": hit["title"],
                }

                all_country_evidence.append(
                    evidence_record
                )

                if country == gold_country:
                    correct_evidence.append(
                        evidence_record
                    )

        has_correct_evidence = (
            len(correct_evidence) > 0
        )

        if correct_evidence:
            first_correct = min(
                correct_evidence,
                key=lambda x: x["rank"],
            )

            first_correct_rank = first_correct["rank"]
            first_correct_title = first_correct["title"]
        else:
            first_correct_rank = ""
            first_correct_title = ""

        if all_country_evidence:
            first_any = min(
                all_country_evidence,
                key=lambda x: x["rank"],
            )

            first_any_country = first_any["country"]
            first_any_rank = first_any["rank"]
            first_any_title = first_any["title"]
        else:
            first_any_country = ""
            first_any_rank = ""
            first_any_title = ""

        if has_correct_evidence:
            evidence_to_reader_result = (
                "correct"
                if reader_outcome == "CORRECT"
                else (
                    "wrong_prediction"
                    if reader_outcome == "INCORRECT"
                    else "abstained"
                )
            )
        else:
            if reader_outcome == "CORRECT":
                evidence_to_reader_result = (
                    "correct_without_explicit_title_evidence"
                )
            elif reader_outcome == "INCORRECT":
                evidence_to_reader_result = (
                    "wrong_without_correct_evidence"
                )
            else:
                evidence_to_reader_result = (
                    "no_correct_evidence_abstained"
                )

        image_rows.append(
            {
                "image_id": image_id,
                "gold_country": gold_country,
                "predicted_country": predicted_country,
                "reader_outcome": reader_outcome,
                "reader_status": reader_status,
                "reader_confidence": safe_float(
                    reader["confidence"]
                ),
                "has_correct_top5_evidence": (
                    has_correct_evidence
                ),
                "correct_evidence_count": len(
                    correct_evidence
                ),
                "first_correct_evidence_rank": (
                    first_correct_rank
                ),
                "first_correct_evidence_title": (
                    first_correct_title
                ),
                "first_any_country": first_any_country,
                "first_any_country_rank": first_any_rank,
                "first_any_country_title": first_any_title,
                "total_country_evidence_mentions": len(
                    all_country_evidence
                ),
                "evidence_to_reader_result": (
                    evidence_to_reader_result
                ),
            }
        )

    # ---------------------------------------------------------
    # Aggregate metrics
    # ---------------------------------------------------------

    total = len(image_rows)

    retrieval_evidence_count = sum(
        row["has_correct_top5_evidence"]
        for row in image_rows
    )

    correct_reader_count = sum(
        row["reader_outcome"] == "CORRECT"
        for row in image_rows
    )

    incorrect_reader_count = sum(
        row["reader_outcome"] == "INCORRECT"
        for row in image_rows
    )

    unknown_reader_count = sum(
        row["reader_outcome"] == "UNKNOWN"
        for row in image_rows
    )

    # Among images where the correct country was actually
    # retrieved, what did the reader do?
    evidence_and_correct = sum(
        row["has_correct_top5_evidence"]
        and row["reader_outcome"] == "CORRECT"
        for row in image_rows
    )

    evidence_and_wrong = sum(
        row["has_correct_top5_evidence"]
        and row["reader_outcome"] == "INCORRECT"
        for row in image_rows
    )

    evidence_and_unknown = sum(
        row["has_correct_top5_evidence"]
        and row["reader_outcome"] == "UNKNOWN"
        for row in image_rows
    )

    no_evidence_but_correct = sum(
        not row["has_correct_top5_evidence"]
        and row["reader_outcome"] == "CORRECT"
        for row in image_rows
    )

    no_evidence_and_wrong = sum(
        not row["has_correct_top5_evidence"]
        and row["reader_outcome"] == "INCORRECT"
        for row in image_rows
    )

    no_evidence_and_unknown = sum(
        not row["has_correct_top5_evidence"]
        and row["reader_outcome"] == "UNKNOWN"
        for row in image_rows
    )

    conversion_rate = (
        evidence_and_correct / retrieval_evidence_count
        if retrieval_evidence_count
        else 0.0
    )

    evidence_available_prediction_rate = (
        (evidence_and_correct + evidence_and_wrong)
        / retrieval_evidence_count
        if retrieval_evidence_count
        else 0.0
    )

    evidence_available_error_rate = (
        evidence_and_wrong / retrieval_evidence_count
        if retrieval_evidence_count
        else 0.0
    )

    evidence_available_abstention_rate = (
        evidence_and_unknown / retrieval_evidence_count
        if retrieval_evidence_count
        else 0.0
    )

    # Reader performance conditional on retrieval evidence.
    conditional_accuracy = conversion_rate

    # How often did the reader make a correct prediction despite
    # no explicit correct-country title being present?
    no_evidence_correct_rate = (
        no_evidence_but_correct / total
        if total
        else 0.0
    )

    # Cross-tabulation.
    cross_tab = {
        "correct_evidence": {
            "reader_correct": evidence_and_correct,
            "reader_incorrect": evidence_and_wrong,
            "reader_unknown": evidence_and_unknown,
        },
        "no_correct_evidence": {
            "reader_correct": no_evidence_but_correct,
            "reader_incorrect": no_evidence_and_wrong,
            "reader_unknown": no_evidence_and_unknown,
        },
    }

    # Distribution of first correct evidence rank.
    rank_distribution = Counter()

    for row in image_rows:
        if row["first_correct_evidence_rank"] != "":
            rank_distribution[
                str(row["first_correct_evidence_rank"])
            ] += 1

    # Per-country comparison.
    country_stats = defaultdict(
        lambda: {
            "n": 0,
            "correct_evidence": 0,
            "reader_correct": 0,
            "reader_incorrect": 0,
            "reader_unknown": 0,
        }
    )

    for row in image_rows:
        country = row["gold_country"]

        country_stats[country]["n"] += 1

        if row["has_correct_top5_evidence"]:
            country_stats[country]["correct_evidence"] += 1

        if row["reader_outcome"] == "CORRECT":
            country_stats[country]["reader_correct"] += 1

        elif row["reader_outcome"] == "INCORRECT":
            country_stats[country]["reader_incorrect"] += 1

        else:
            country_stats[country]["reader_unknown"] += 1

    per_country = {}

    for country in sorted(country_stats):
        stats = country_stats[country]
        n = stats["n"]
        evidence_n = stats["correct_evidence"]

        per_country[country] = {
            "n": n,
            "correct_top5_evidence": evidence_n,
            "retrieval_evidence_rate": (
                evidence_n / n if n else 0.0
            ),
            "reader_correct": stats["reader_correct"],
            "reader_incorrect": stats["reader_incorrect"],
            "reader_unknown": stats["reader_unknown"],
            "reader_accuracy": (
                stats["reader_correct"] / n
                if n
                else 0.0
            ),
            "evidence_to_correct_conversion": (
                stats["reader_correct"] / evidence_n
                if evidence_n
                else 0.0
            ),
        }

    metrics = {
        "experiment": "phase6_retrieval_reader_comparison",
        "total_images": total,

        "retrieval": {
            "correct_top5_evidence": retrieval_evidence_count,
            "correct_top5_evidence_rate": (
                retrieval_evidence_count / total
                if total
                else 0.0
            ),
            "first_correct_evidence_rank_distribution": dict(
                sorted(rank_distribution.items())
            ),
        },

        "reader": {
            "correct": correct_reader_count,
            "incorrect": incorrect_reader_count,
            "unknown": unknown_reader_count,
            "overall_accuracy": (
                correct_reader_count / total
                if total
                else 0.0
            ),
            "coverage": (
                (correct_reader_count + incorrect_reader_count)
                / total
                if total
                else 0.0
            ),
            "selective_accuracy": (
                correct_reader_count
                / (correct_reader_count + incorrect_reader_count)
                if (correct_reader_count + incorrect_reader_count)
                else 0.0
            ),
        },

        "evidence_to_reader": {
            "images_with_correct_evidence": (
                retrieval_evidence_count
            ),
            "reader_correct_given_correct_evidence": (
                evidence_and_correct
            ),
            "reader_wrong_given_correct_evidence": (
                evidence_and_wrong
            ),
            "reader_unknown_given_correct_evidence": (
                evidence_and_unknown
            ),
            "correct_evidence_to_correct_prediction_rate": (
                conversion_rate
            ),
            "correct_evidence_to_any_prediction_rate": (
                evidence_available_prediction_rate
            ),
            "correct_evidence_to_wrong_prediction_rate": (
                evidence_available_error_rate
            ),
            "correct_evidence_to_unknown_rate": (
                evidence_available_abstention_rate
            ),
        },

        "no_correct_evidence": {
            "reader_correct": no_evidence_but_correct,
            "reader_incorrect": no_evidence_and_wrong,
            "reader_unknown": no_evidence_and_unknown,
            "reader_correct_rate": no_evidence_correct_rate,
        },

        "cross_tab": cross_tab,

        "per_country": per_country,
    }

    # Save image-level analysis.
    fieldnames = list(image_rows[0].keys())

    with IMAGE_OUTPUT.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(image_rows)

    # Save metrics.
    with METRICS_OUTPUT.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            metrics,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # Console summary.
    print()
    print("Phase 6 quantitative comparison complete.")
    print()
    print(f"Images evaluated: {total}")
    print()
    print("RETRIEVAL")
    print(
        f"Correct Top-5 evidence: "
        f"{retrieval_evidence_count}/{total} "
        f"({retrieval_evidence_count / total:.3f})"
    )
    print()
    print("READER")
    print(
        f"Correct: {correct_reader_count}/{total}"
    )
    print(
        f"Incorrect: {incorrect_reader_count}/{total}"
    )
    print(
        f"UNKNOWN: {unknown_reader_count}/{total}"
    )
    print()
    print("EVIDENCE -> READER")
    print(
        f"Correct evidence + correct reader: "
        f"{evidence_and_correct}"
    )
    print(
        f"Correct evidence + wrong reader: "
        f"{evidence_and_wrong}"
    )
    print(
        f"Correct evidence + UNKNOWN: "
        f"{evidence_and_unknown}"
    )
    print(
        f"Evidence-to-correct conversion: "
        f"{conversion_rate:.3f}"
    )
    print(
        f"Evidence-to-any-prediction: "
        f"{evidence_available_prediction_rate:.3f}"
    )
    print()
    print("NO CORRECT RETRIEVAL EVIDENCE")
    print(
        f"Reader correct anyway: "
        f"{no_evidence_but_correct}"
    )
    print(
        f"Reader incorrect: "
        f"{no_evidence_and_wrong}"
    )
    print(
        f"Reader UNKNOWN: "
        f"{no_evidence_and_unknown}"
    )
    print()
    print(f"Saved: {IMAGE_OUTPUT}")
    print(f"Saved: {METRICS_OUTPUT}")


if __name__ == "__main__":
    main()