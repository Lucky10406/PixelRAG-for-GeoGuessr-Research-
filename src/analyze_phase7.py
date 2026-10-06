import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

METADATA_PATH = ROOT / "data" / "eval_metadata.csv"
HITS_PATH = ROOT / "results" / "retrieval_hits.csv"
PHASE6_PATH = ROOT / "results" / "phase6_image_analysis.csv"
READER_PATH = ROOT / "results" / "reader_predictions.csv"

OUTPUT_PATH = ROOT / "results" / "phase7_failure_analysis.csv"
SUMMARY_PATH = ROOT / "results" / "phase7_failure_summary.json"


# Same strict country aliases used in Phases 4-6.
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


# Countries that can reasonably create geographic confusion in this benchmark.
# This is deliberately conservative.
RELATED_GROUPS = [
    {"Botswana", "South Africa", "Eswatini"},
    {"Argentina", "Uruguay"},
    {"United States", "Puerto Rico"},
    {"United Kingdom", "Ireland"},
    {"South Korea", "North Korea"},
    {"France", "Luxembourg"},
    {"Andorra", "France"},
    {"Andorra", "Spain"},
    {"Switzerland", "France"},
    {"Montenegro", "Albania"},
    {"Montenegro", "Croatia"},
    {"Bulgaria", "Montenegro"},
    {"Cambodia", "Thailand"},
    {"Cambodia", "Vietnam"},
]


GENERIC_PATTERNS = [
    "geoguessr",
    "google street view",
    "google_street_view",
    "google maps",
    "google_maps",
    "street view coverage",
    "street_view_coverage",
    "google street view coverage",
    "selected picture",
    "selected_picture",
    "featured picture",
    "featured_picture",
    "geography/featured picture archive",
    "portal:geography",
    "portal:roads",
    "portal:geography",
]


ROAD_PATTERNS = [
    "highway",
    "road",
    "roads",
    "route",
    "motorway",
    "street",
    "avenue",
    "junction",
    "r511",
    "r24",
    "m-4.1",
]


LANDMARK_PATTERNS = [
    "tower",
    "museum",
    "palace",
    "castle",
    "temple",
    "monument",
    "landmark",
    "bridge",
    "stadium",
    "building",
    "church",
    "mosque",
    "cathedral",
]


TEXT_PATTERNS = [
    "road signs",
    "road_signs",
    "sign",
    "signs",
    "language",
    "alphabet",
    "license plate",
    "licence plate",
]


def normalize(text):
    text = str(text or "").lower()
    text = text.replace("_", " ")
    return re.sub(r"\s+", " ", text).strip()


def contains_any(text, patterns):
    text = normalize(text)
    return any(p in text for p in patterns)


def find_country_mentions(title):
    normalized = normalize(title)
    found = []

    for country, aliases in COUNTRY_ALIASES.items():
        for alias in aliases:
            if normalize(alias) in normalized:
                found.append(country)
                break

    return found


def countries_related(a, b):
    if not a or not b or a == b:
        return False

    for group in RELATED_GROUPS:
        if a in group and b in group:
            return True

    return False


def load_csv(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def classify_retrieval_failure(gold_country, hits):
    """
    Classify the retrieval-side failure.

    This classification deliberately uses only information available
    from retrieval metadata/titles. It does NOT claim to infer visual
    ambiguity from titles alone.
    """

    titles = [h["title"] for h in hits if h.get("title")]
    combined = " | ".join(titles)

    mentioned_wrong_countries = []

    for title in titles:
        for country in find_country_mentions(title):
            if country != gold_country and country not in mentioned_wrong_countries:
                mentioned_wrong_countries.append(country)

    # Strongest signal: an explicit wrong country appears.
    if mentioned_wrong_countries:
        related = [
            c for c in mentioned_wrong_countries
            if countries_related(gold_country, c)
        ]

        if related:
            return (
                "geographically_related_wrong_evidence",
                f"Wrong-country evidence: {', '.join(related)}",
            )

        if contains_any(combined, ROAD_PATTERNS):
            return (
                "wrong_country_transport_or_road",
                f"Wrong-country road/transport evidence: {', '.join(mentioned_wrong_countries)}",
            )

        return (
            "wrong_country_specific_evidence",
            f"Wrong-country evidence: {', '.join(mentioned_wrong_countries)}",
        )

    # Generic retrieval dominated by mapping / Street View pages.
    generic_count = sum(
        contains_any(title, GENERIC_PATTERNS)
        for title in titles
    )

    if generic_count >= 2:
        return (
            "generic_retrieval",
            "Multiple generic Street View / mapping / GeoGuessr results",
        )

    # Road/transport retrieval without an explicit country match.
    road_count = sum(
        contains_any(title, ROAD_PATTERNS)
        for title in titles
    )

    if road_count >= 2:
        return (
            "transport_or_road_without_country_clue",
            "Multiple road/highway/route results without correct country evidence",
        )

    # Landmark-specific retrieval.
    landmark_count = sum(
        contains_any(title, LANDMARK_PATTERNS)
        for title in titles
    )

    if landmark_count >= 1:
        return (
            "landmark_or_location_bias",
            "Specific landmark/location result, but no correct-country evidence",
        )

    # Text-related pages are interesting for later manual inspection.
    text_count = sum(
        contains_any(title, TEXT_PATTERNS)
        for title in titles
    )

    if text_count >= 1:
        return (
            "possible_text_signal_not_resolved",
            "Text/sign-related result exists but does not identify the correct country",
        )

    return (
        "weak_or_non_specific_retrieval",
        "No strong geographic clue visible in retrieved titles",
    )


def main():
    metadata = load_csv(METADATA_PATH)
    hits_rows = load_csv(HITS_PATH)
    phase6_rows = load_csv(PHASE6_PATH)
    reader_rows = load_csv(READER_PATH)

    metadata_by_id = {
        row["image_id"]: row
        for row in metadata
    }

    phase6_by_id = {
        row["image_id"]: row
        for row in phase6_rows
    }

    reader_by_id = {
        row["image_id"]: row
        for row in reader_rows
    }

    hits_by_id = defaultdict(list)

    for row in hits_rows:
        hits_by_id[row["image_id"]].append(row)

    output_rows = []

    for image_id, meta in metadata_by_id.items():
        gold = meta["country"]

        hits = sorted(
            hits_by_id.get(image_id, []),
            key=lambda x: int(x.get("rank", 999))
        )

        phase6 = phase6_by_id.get(image_id, {})
        reader = reader_by_id.get(image_id, {})

        predicted = reader.get("predicted_country", "UNKNOWN")

        # Only analyze actual retrieval failures here.
        correct_evidence = phase6.get("first_correct_evidence_rank", "")

        if correct_evidence:
            retrieval_failure_type = "not_a_retrieval_failure"
            retrieval_reason = "Correct country evidence was present in Top-5"
        else:
            retrieval_failure_type, retrieval_reason = classify_retrieval_failure(
                gold,
                hits,
            )

        # Reader-side classification.
        if predicted == "UNKNOWN":
            reader_outcome = "UNKNOWN"
        elif predicted == gold:
            reader_outcome = "CORRECT"
        else:
            reader_outcome = "INCORRECT"

        # For the 25 incorrect reader predictions, identify the wrong country.
        wrong_prediction_country = ""
        wrong_prediction_related = False

        if reader_outcome == "INCORRECT":
            wrong_prediction_country = predicted
            wrong_prediction_related = countries_related(
                gold,
                predicted,
            )

        # Reader failure type.
        if reader_outcome == "CORRECT":
            reader_failure_type = "not_a_reader_failure"
        elif reader_outcome == "UNKNOWN":
            reader_failure_type = "reader_abstention"
        else:
            if wrong_prediction_related:
                reader_failure_type = "wrong_clue_geographically_related"
            elif contains_any(
                reader.get("evidence_title", ""),
                GENERIC_PATTERNS,
            ):
                reader_failure_type = "wrong_generic_clue"
            elif contains_any(
                reader.get("evidence_title", ""),
                ROAD_PATTERNS,
            ):
                reader_failure_type = "wrong_transport_or_road_clue"
            elif contains_any(
                reader.get("evidence_title", ""),
                LANDMARK_PATTERNS,
            ):
                reader_failure_type = "wrong_landmark_or_location_clue"
            else:
                reader_failure_type = "wrong_specific_clue"

        output_rows.append({
            "image_id": image_id,
            "gold_country": gold,
            "predicted_country": predicted,
            "reader_outcome": reader_outcome,
            "retrieval_failure_type": retrieval_failure_type,
            "retrieval_reason": retrieval_reason,
            "reader_failure_type": reader_failure_type,
            "wrong_prediction_country": wrong_prediction_country,
            "wrong_prediction_geographically_related": str(
                wrong_prediction_related
            ),
            "evidence_rank": reader.get("evidence_rank", ""),
            "evidence_title": reader.get("evidence_title", ""),
            "top5_titles": " || ".join(
                f"r{h.get('rank', '')}: {h.get('title', '')}"
                for h in hits
            ),
            "manual_review_needed": (
                "yes"
                if retrieval_failure_type in {
                    "weak_or_non_specific_retrieval",
                    "possible_text_signal_not_resolved",
                    "landmark_or_location_bias",
                }
                else "no"
            ),
        })

    # Keep output deterministic.
    output_rows.sort(key=lambda x: x["image_id"])

    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=output_rows[0].keys(),
        )
        writer.writeheader()
        writer.writerows(output_rows)

    # ---------------------------------------------------------
    # Summary statistics
    # ---------------------------------------------------------

    total = len(output_rows)

    retrieval_failures = [
        r for r in output_rows
        if r["retrieval_failure_type"] != "not_a_retrieval_failure"
    ]

    reader_incorrect = [
        r for r in output_rows
        if r["reader_outcome"] == "INCORRECT"
    ]

    reader_unknown = [
        r for r in output_rows
        if r["reader_outcome"] == "UNKNOWN"
    ]

    retrieval_counts = Counter(
        r["retrieval_failure_type"]
        for r in retrieval_failures
    )

    reader_failure_counts = Counter(
        r["reader_failure_type"]
        for r in reader_incorrect
    )

    related_wrong_reader = sum(
        r["wrong_prediction_geographically_related"] == "True"
        for r in reader_incorrect
    )

    manual_review = sum(
        r["manual_review_needed"] == "yes"
        for r in retrieval_failures
    )

    summary = {
        "experiment": "phase7_failure_analysis",
        "total_images": total,

        "retrieval_failures": {
            "count": len(retrieval_failures),
            "rate": len(retrieval_failures) / total if total else 0,
            "categories": dict(retrieval_counts),
        },

        "reader_incorrect": {
            "count": len(reader_incorrect),
            "rate": len(reader_incorrect) / total if total else 0,
            "categories": dict(reader_failure_counts),
            "geographically_related_wrong_predictions": related_wrong_reader,
        },

        "reader_unknown": {
            "count": len(reader_unknown),
            "rate": len(reader_unknown) / total if total else 0,
        },

        "manual_review": {
            "retrieval_cases_flagged": manual_review,
        },

        "methodology_notes": [
            "Retrieval failure is defined as no explicit gold-country evidence in the Top-5 titles.",
            "Automated categories use retrieval titles and metadata only.",
            "Visual ambiguity cannot be established reliably without inspecting the original image.",
            "Text-missed failure cannot be established because useful_visible_text is currently unannotated.",
            "Manual review is therefore required before treating the taxonomy as final.",
            "Reader-side categories describe the evidence selected by the deterministic reader.",
        ],
    }

    with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print()
    print("Phase 7 preliminary failure analysis complete.")
    print()
    print(f"Images evaluated: {total}")
    print()
    print("RETRIEVAL FAILURES")
    print(f"Cases without correct Top-5 evidence: {len(retrieval_failures)}")
    for category, count in retrieval_counts.most_common():
        pct = count / len(retrieval_failures) * 100 if retrieval_failures else 0
        print(f"  {category}: {count} ({pct:.1f}%)")

    print()
    print("READER INCORRECT")
    print(f"Incorrect predictions: {len(reader_incorrect)}")
    for category, count in reader_failure_counts.most_common():
        pct = count / len(reader_incorrect) * 100 if reader_incorrect else 0
        print(f"  {category}: {count} ({pct:.1f}%)")

    print()
    print(
        "Geographically related wrong reader predictions:",
        related_wrong_reader,
    )

    print()
    print("MANUAL REVIEW")
    print(
        "Retrieval cases flagged for manual inspection:",
        manual_review,
    )

    print()
    print(f"Saved: {OUTPUT_PATH}")
    print(f"Saved: {SUMMARY_PATH}")


if __name__ == "__main__":
    main()