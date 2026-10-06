import csv
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

RETRIEVAL_FILE = ROOT / "results" / "retrieval_hits.csv"
TEXT_FILE = ROOT / "results" / "text_aware_records.jsonl"
OUTPUT_FILE = ROOT / "results" / "phase9_text_vs_image.csv"
SUMMARY_FILE = ROOT / "results" / "phase9_metrics.json"


COUNTRY_ALIASES = {
    "Andorra": ["andorra"],
    "Argentina": ["argentina"],
    "Botswana": ["botswana"],
    "Bulgaria": ["bulgaria"],
    "Cambodia": ["cambodia"],
    "China": ["china"],
    "Ecuador": ["ecuador"],
    "Estonia": ["estonia"],
    "Eswatini": ["eswatini"],
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
    return re.sub(r"[^a-z0-9_. -]+", " ", str(text).lower()).strip()


def country_in_title(title, country):
    title = normalize(title)

    for alias in COUNTRY_ALIASES.get(country, []):
        alias = normalize(alias)

        if " " in alias:
            if alias in title:
                return True
        else:
            tokens = set(title.replace("_", " ").split())
            if alias in tokens:
                return True

    return False


def first_country_evidence(titles, gold):
    for rank, title in enumerate(titles, start=1):
        if country_in_title(title, gold):
            return rank

    return None


def load_image_baseline():
    records = {}

    with open(RETRIEVAL_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            image_id = row["image_id"]

            if image_id not in records:
                records[image_id] = {
                    "gold_country": row["country"],
                    "titles": [],
                }

            records[image_id]["titles"].append(row["title"])

    return records


def load_text_records():
    records = {}

    with open(TEXT_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            record = json.loads(line)

            if record.get("status") != "SUCCESS":
                continue

            image_id = record["image_id"]

            titles = []

            for response in record.get("responses", []):
                for result in response.get("results", []):
                    for hit in result.get("hits", []):
                        title = hit.get("url") or hit.get("title")

                        if title:
                            titles.append(title)

            records[image_id] = {
                "gold_country": record["gold_country"],
                "ocr": record.get("useful_text", []),
                "titles": titles,
            }

    return records


def main():
    image_records = load_image_baseline()
    text_records = load_text_records()

    rows = []

    for image_id, text_record in text_records.items():
        gold = text_record["gold_country"]

        image = image_records.get(image_id, {
            "gold_country": gold,
            "titles": [],
        })

        image_titles = image["titles"][:5]
        text_titles = text_record["titles"][:5]

        image_rank = first_country_evidence(image_titles, gold)
        text_rank = first_country_evidence(text_titles, gold)

        image_correct = image_rank is not None
        text_correct = text_rank is not None

        if image_correct and text_correct:
            outcome = "both_correct"
        elif not image_correct and text_correct:
            outcome = "text_added_correct_evidence"
        elif image_correct and not text_correct:
            outcome = "image_only_correct_evidence"
        else:
            outcome = "neither_correct"

        rows.append({
            "image_id": image_id,
            "gold_country": gold,
            "ocr_text": " | ".join(text_record["ocr"]),
            "image_only_correct": image_correct,
            "image_only_first_correct_rank": image_rank or "",
            "text_aware_correct": text_correct,
            "text_aware_first_correct_rank": text_rank or "",
            "outcome": outcome,
            "image_only_top5": " || ".join(image_titles),
            "text_aware_top5": " || ".join(text_titles),
        })

    rows.sort(key=lambda x: x["image_id"])

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    counts = {
        "text_aware_success_cases": len(rows),
        "image_only_correct": sum(r["image_only_correct"] for r in rows),
        "text_aware_correct": sum(r["text_aware_correct"] for r in rows),
        "both_correct": sum(r["outcome"] == "both_correct" for r in rows),
        "text_added_correct_evidence": sum(
            r["outcome"] == "text_added_correct_evidence" for r in rows
        ),
        "image_only_correct_evidence": sum(
            r["outcome"] == "image_only_correct_evidence" for r in rows
        ),
        "neither_correct": sum(
            r["outcome"] == "neither_correct" for r in rows
        ),
    }

    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(counts, f, indent=2)

    print("Phase 9 text-vs-image comparison complete.")
    print()
    print(f"Text-aware success cases: {len(rows)}")
    print(f"Image-only correct evidence: {counts['image_only_correct']}")
    print(f"Text-aware correct evidence: {counts['text_aware_correct']}")
    print(f"Both correct: {counts['both_correct']}")
    print(
        "Text added correct evidence:",
        counts["text_added_correct_evidence"],
    )
    print(
        "Image-only correct evidence:",
        counts["image_only_correct_evidence"],
    )
    print(f"Neither correct: {counts['neither_correct']}")
    print()
    print(f"Saved: {OUTPUT_FILE}")
    print(f"Saved: {SUMMARY_FILE}")

    print()
    print("CASE DETAILS")
    for row in rows:
        print()
        print(row["image_id"], "|", row["gold_country"])
        print("OCR:", row["ocr_text"])
        print(
            "Image-only:",
            row["image_only_first_correct_rank"] or "NO CORRECT EVIDENCE",
        )
        print(
            "Text-aware:",
            row["text_aware_first_correct_rank"] or "NO CORRECT EVIDENCE",
        )
        print("Outcome:", row["outcome"])


if __name__ == "__main__":
    main()