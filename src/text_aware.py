import argparse
import json
import re
import time
from pathlib import Path

import easyocr
import numpy as np
import pandas as pd
import requests
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]

API_URL = "https://api.pixelrag.ai/search"

METADATA_PATH = ROOT / "data" / "eval_metadata.csv"
OUTPUT_PATH = ROOT / "results" / "text_aware_records.jsonl"


# Common GeoGuessr / Google Street View UI text
# that should not be treated as geographic evidence.
UI_PHRASES = [
    "map",
    "round",
    "score",
    "world",
    "google",
    "terms of use",
    "term of use",
    "map data",
    "keyboard shortcut",
    "keyboard shortcuts",
    "guess",
    "guessr",
    "street view",
    "north america",
    "south america",
    "2021",
]


def looks_like_garbage(text):
    """
    Reject OCR fragments that are too short or clearly noisy.
    """

    text = text.strip()

    # Ignore very short fragments such as TEMP, MAP, etc.
    if len(text) < 5:
        return True

    letters = [
        character
        for character in text
        if character.isalpha()
    ]

    # Require at least three alphabetic characters.
    if len(letters) < 3:
        return True

    # Reject text containing too many unusual symbols.
    alnum = sum(
        character.isalnum()
        for character in text
    )

    if len(text) > 0 and alnum / len(text) < 0.65:
        return True

    # Reject obvious repeated-character OCR noise.
    if re.search(r"(.)\1\1", text.lower()):
        return True

    return False


def is_ui_text(text):
    """
    Check whether OCR text looks like GeoGuessr / Google UI text.
    """

    normalized = re.sub(
        r"\s+",
        " ",
        text.strip().lower(),
    )

    for phrase in UI_PHRASES:
        if phrase in normalized:
            return True

    return False


def clean_ocr_text(results):
    """
    Convert EasyOCR output into:
      1. raw OCR text + confidence
      2. filtered useful text
    """

    raw_text = []
    useful_text = []

    for item in results:

        if len(item) < 3:
            continue

        text = str(item[1]).strip()

        confidence = float(item[2])

        if text:
            raw_text.append(
                {
                    "text": text,
                    "confidence": round(
                        confidence,
                        4,
                    ),
                }
            )

        # Conservative OCR confidence threshold.
        if confidence < 0.55:
            continue

        if not text:
            continue

        if is_ui_text(text):
            continue

        if looks_like_garbage(text):
            continue

        useful_text.append(text)

    # Remove duplicate OCR fragments while
    # preserving their original order.
    final_text = []

    seen = set()

    for text in useful_text:

        key = text.lower()

        if key not in seen:
            seen.add(key)
            final_text.append(text)

    return raw_text, final_text


def extract_text(reader, image_path):
    """
    Run EasyOCR on the central gameplay region.

    We avoid the extreme edges because GeoGuessr UI
    elements are commonly located there.
    """

    image = Image.open(
        image_path
    ).convert("RGB")

    width, height = image.size

    # Crop away a small amount of the outer UI.
    left = int(width * 0.05)
    top = int(height * 0.08)
    right = int(width * 0.95)
    bottom = int(height * 0.90)

    cropped = image.crop(
        (
            left,
            top,
            right,
            bottom,
        )
    )

    # EasyOCR accepts numpy arrays, not PIL Image objects.
    cropped_array = np.array(
        cropped
    )

    results = reader.readtext(
        cropped_array
    )

    return clean_ocr_text(
        results
    )


def query_pixelrag(text):
    """
    Query the hosted PixelRAG API using OCR text.
    """

    payload = {
        "queries": [
            {
                "text": text
            }
        ],
        "n_docs": 5,
    }

    response = requests.post(
        API_URL,
        json=payload,
        timeout=120,
    )

    response.raise_for_status()

    return response.json()


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Number of images to process.",
    )

    args = parser.parse_args()

    metadata = pd.read_csv(
        METADATA_PATH
    )

    if args.limit is not None:
        metadata = metadata.head(
            args.limit
        )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        f"Images selected: {len(metadata)}"
    )

    print(
        "Loading EasyOCR..."
    )

    reader = easyocr.Reader(
        ["en"],
        gpu=False,
    )

    processed = 0

    with open(
        OUTPUT_PATH,
        "w",
        encoding="utf-8",
    ) as output_file:

        for index, (_, row) in enumerate(
            metadata.iterrows(),
            start=1,
        ):

            image_id = row["image_id"]

            image_path = (
                ROOT / row["image_path"]
            )

            print(
                f"[{index}/{len(metadata)}] {image_id}"
            )

            start_time = time.time()

            try:

                raw_ocr, useful_text = (
                    extract_text(
                        reader,
                        image_path,
                    )
                )

                record = {
                    "image_id": image_id,
                    "image_path": row[
                        "image_path"
                    ],
                    "gold_country": row[
                        "country"
                    ],
                    "raw_ocr": raw_ocr,
                    "useful_text": useful_text,
                    "queries": [],
                    "responses": [],
                    "status": "NO_USEFUL_TEXT",
                    "latency_seconds": 0.0,
                }

                print(
                    f"  Useful text: {useful_text}"
                )

                if useful_text:

                    query_text = " ".join(
                        useful_text
                    )

                    record["queries"] = [
                        query_text
                    ]

                    api_start = time.time()

                    response = query_pixelrag(
                        query_text
                    )

                    record["responses"] = [
                        response
                    ]

                    record["status"] = (
                        "SUCCESS"
                    )

                    record[
                        "latency_seconds"
                    ] = round(
                        time.time()
                        - api_start,
                        3,
                    )

                total_time = (
                    time.time()
                    - start_time
                )

                print(
                    f"  Status: {record['status']}"
                )

                print(
                    f"  Time: {total_time:.2f}s"
                )

            except Exception as exc:

                record = {
                    "image_id": image_id,
                    "image_path": row[
                        "image_path"
                    ],
                    "gold_country": row[
                        "country"
                    ],
                    "raw_ocr": [],
                    "useful_text": [],
                    "queries": [],
                    "responses": [],
                    "status": "ERROR",
                    "error": str(exc),
                    "latency_seconds": 0.0,
                }

                print(
                    f"  ERROR: {exc}"
                )

            output_file.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )

            output_file.flush()

            processed += 1

    print()
    print(
        "Phase 8 cleaned OCR/text retrieval complete."
    )

    print(
        f"Processed: {processed}"
    )

    print(
        f"Saved: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()