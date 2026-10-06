"""
Phase 5: Evaluate deterministic reader predictions.

Compares reader predictions against the frozen evaluation labels.

Important:
The gold country is used ONLY here for evaluation.
It is never used by run_reader.py to make predictions.
"""

from pathlib import Path
import csv
import json
from collections import defaultdict


PROJECT_ROOT = Path(__file__).resolve().parents[1]

METADATA_FILE = PROJECT_ROOT / "data" / "eval_metadata.csv"
PREDICTIONS_FILE = PROJECT_ROOT / "results" / "reader_predictions.csv"

OUTPUT_FILE = PROJECT_ROOT / "results" / "reader_metrics.json"


def load_metadata():
    """Load gold countries from frozen evaluation metadata."""

    metadata = {}

    with METADATA_FILE.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as f:
        reader = csv.DictReader(f)

        for row in reader:
            metadata[row["image_id"]] = row["country"]

    return metadata


def load_predictions():
    """Load reader predictions."""

    predictions = {}

    with PREDICTIONS_FILE.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as f:
        reader = csv.DictReader(f)

        for row in reader:
            predictions[row["image_id"]] = row

    return predictions


def main():
    gold = load_metadata()
    predictions = load_predictions()

    image_ids = sorted(gold.keys())

    total = len(image_ids)

    correct = 0
    predicted = 0
    unknown = 0

    per_country = defaultdict(
        lambda: {
            "n": 0,
            "correct": 0,
            "incorrect": 0,
            "unknown": 0,
        }
    )

    examples_correct = []
    examples_incorrect = []
    examples_unknown = []

    for image_id in image_ids:
        gold_country = gold[image_id]

        if image_id not in predictions:
            raise ValueError(
                f"Missing prediction for image: {image_id}"
            )

        prediction_row = predictions[image_id]
        predicted_country = prediction_row[
            "predicted_country"
        ]

        per_country[gold_country]["n"] += 1

        if predicted_country == "UNKNOWN":
            unknown += 1
            per_country[gold_country]["unknown"] += 1

            if len(examples_unknown) < 10:
                examples_unknown.append(
                    {
                        "image_id": image_id,
                        "gold_country": gold_country,
                        "predicted_country": predicted_country,
                        "evidence_title": prediction_row[
                            "evidence_title"
                        ],
                    }
                )

        else:
            predicted += 1

            if predicted_country == gold_country:
                correct += 1
                per_country[gold_country]["correct"] += 1

                if len(examples_correct) < 10:
                    examples_correct.append(
                        {
                            "image_id": image_id,
                            "gold_country": gold_country,
                            "predicted_country": predicted_country,
                            "confidence": prediction_row[
                                "confidence"
                            ],
                            "evidence_rank": prediction_row[
                                "evidence_rank"
                            ],
                            "evidence_title": prediction_row[
                                "evidence_title"
                            ],
                        }
                    )

            else:
                per_country[gold_country]["incorrect"] += 1

                if len(examples_incorrect) < 10:
                    examples_incorrect.append(
                        {
                            "image_id": image_id,
                            "gold_country": gold_country,
                            "predicted_country": predicted_country,
                            "confidence": prediction_row[
                                "confidence"
                            ],
                            "evidence_rank": prediction_row[
                                "evidence_rank"
                            ],
                            "evidence_title": prediction_row[
                                "evidence_title"
                            ],
                        }
                    )

    overall_accuracy = correct / total if total else 0.0

    coverage = predicted / total if total else 0.0

    selective_accuracy = (
        correct / predicted
        if predicted
        else 0.0
    )

    abstention_rate = unknown / total if total else 0.0

    country_results = {}

    for country in sorted(per_country.keys()):
        stats = per_country[country]

        n = stats["n"]

        country_results[country] = {
            "n": n,
            "correct": stats["correct"],
            "incorrect": stats["incorrect"],
            "unknown": stats["unknown"],
            "accuracy": (
                stats["correct"] / n
                if n
                else 0.0
            ),
            "coverage": (
                (n - stats["unknown"]) / n
                if n
                else 0.0
            ),
        }

    metrics = {
        "experiment": "phase5_deterministic_reader",
        "reader_type": "rank_weighted_explicit_country_title_match",
        "total_images": total,
        "correct_predictions": correct,
        "non_unknown_predictions": predicted,
        "unknown_predictions": unknown,
        "overall_accuracy": overall_accuracy,
        "coverage": coverage,
        "selective_accuracy": selective_accuracy,
        "abstention_rate": abstention_rate,
        "per_country": country_results,
        "examples": {
            "correct": examples_correct,
            "incorrect": examples_incorrect,
            "unknown": examples_unknown,
        },
    }

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            metrics,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print("Phase 5 reader evaluation complete.")
    print()
    print(f"Images evaluated: {total}")
    print(
        f"Correct predictions: "
        f"{correct}/{total}"
    )
    print(
        f"Overall accuracy: "
        f"{overall_accuracy:.3f}"
    )
    print(
        f"Coverage: "
        f"{coverage:.3f}"
    )
    print(
        f"Selective accuracy: "
        f"{selective_accuracy:.3f}"
    )
    print(
        f"Abstention rate: "
        f"{abstention_rate:.3f}"
    )
    print()
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()