from __future__ import annotations

import argparse
import base64
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]

METADATA_PATH = ROOT / "data" / "eval_metadata.csv"
RESULTS_DIR = ROOT / "results"

RAW_RESULTS_PATH = RESULTS_DIR / "retrieval_records.jsonl"
HITS_PATH = RESULTS_DIR / "retrieval_hits.csv"

API_URL = "https://api.pixelrag.ai/search"

TOP_K = 5


def load_metadata() -> list[dict]:
    if not METADATA_PATH.exists():
        raise FileNotFoundError(
            f"Missing metadata file: {METADATA_PATH}"
        )

    with METADATA_PATH.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as f:
        return list(csv.DictReader(f))


def encode_image(path: Path) -> str:
    with path.open("rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def query_pixelrag(image_path: Path, n_docs: int = TOP_K) -> dict:
    image_b64 = encode_image(image_path)

    payload = {
        "queries": [
            {
                "image": image_b64
            }
        ],
        "n_docs": n_docs,
    }

    body = json.dumps(payload).encode("utf-8")

    request = Request(
        API_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    start = time.perf_counter()

    with urlopen(request, timeout=120) as response:
        response_body = response.read()

    elapsed = time.perf_counter() - start

    result = json.loads(response_body.decode("utf-8"))

    return {
        "response": result,
        "latency_seconds": elapsed,
    }


def get_hits(response: dict) -> list:
    """Extract hits from the hosted PixelRAG response."""

    if not isinstance(response, dict):
        return []

    # Current hosted API format:
    # {
    #   "results": [
    #       {
    #           "hits": [...]
    #       }
    #   ]
    # }
    results = response.get("results")

    if isinstance(results, list):
        for result in results:
            if isinstance(result, dict):
                hits = result.get("hits")

                if isinstance(hits, list):
                    return hits

    # Defensive fallbacks for possible future API formats.
    hits = response.get("hits")

    if isinstance(hits, list):
        return hits

    return []


def write_raw_record(record: dict) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    with RAW_RESULTS_PATH.open(
        "a",
        encoding="utf-8",
    ) as f:
        f.write(
            json.dumps(
                record,
                ensure_ascii=False,
            )
            + "\n"
        )


def write_hit_rows(rows: list[dict]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "image_id",
        "country",
        "rank",
        "score",
        "article_id",
        "tile_index",
        "chunk_index",
        "title",
        "url",
        "raw_hit",
    ]

    file_exists = HITS_PATH.exists()

    with HITS_PATH.open(
        "a",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        if not file_exists:
            writer.writeheader()

        writer.writerows(rows)


def extract_field(hit: dict, field: str):
    value = hit.get(field)

    if value is not None:
        return value

    # Some API versions may use metadata nesting.
    metadata = hit.get("metadata")

    if isinstance(metadata, dict):
        return metadata.get(field)

    return None


def process_one(record: dict) -> None:
    image_id = record["image_id"]
    country = record["country"]

    image_path = ROOT / record["image_path"]

    if not image_path.exists():
        raise FileNotFoundError(
            f"Image does not exist: {image_path}"
        )

    print(
        f"\nQuerying {image_id} "
        f"({country})"
    )
    print(
        f"Image: {image_path}"
    )

    result = query_pixelrag(
        image_path,
        n_docs=TOP_K,
    )

    response = result["response"]
    latency = result["latency_seconds"]

    hits = get_hits(response)

    raw_record = {
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "image_id": image_id,
        "country": country,
        "image_path": record["image_path"],
        "top_k": TOP_K,
        "latency_seconds": latency,
        "response": response,
    }

    write_raw_record(raw_record)

    rows = []

    for rank, hit in enumerate(
        hits,
        start=1,
    ):
        if not isinstance(hit, dict):
            hit = {
                "value": hit
            }

        rows.append(
            {
                "image_id": image_id,
                "country": country,
                "rank": rank,
                "score": extract_field(
                    hit,
                    "score",
                ),
                "article_id": extract_field(
                    hit,
                    "article_id",
                ),
                "tile_index": extract_field(
                    hit,
                    "tile_index",
                ),
                "chunk_index": extract_field(
                    hit,
                    "chunk_index",
                ),
                "title": extract_field(
                    hit,
                    "url",
                ),
                "url": extract_field(
                    hit,
                    "url",
                ),
                "raw_hit": json.dumps(
                    hit,
                    ensure_ascii=False,
                ),
            }
        )

    write_hit_rows(rows)

    print(
        f"Status: SUCCESS"
    )
    print(
        f"Retrieved hits: {len(hits)}"
    )
    print(
        f"Latency: {latency:.2f}s"
    )

    for i, hit in enumerate(
        hits,
        start=1,
    ):
        if isinstance(hit, dict):
            print(
                f"  {i}. "
                f"article_id="
                f"{extract_field(hit, 'article_id')} "
                f"score="
                f"{extract_field(hit, 'score')}"
            )
        else:
            print(
                f"  {i}. {hit}"
            )


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--limit",
        type=int,
        default=1,
        help=(
            "Number of images to process. "
            "Default: 1."
        ),
    )

    args = parser.parse_args()

    metadata = load_metadata()

    if args.limit <= 0:
        raise ValueError(
            "--limit must be greater than 0"
        )

    records = metadata[:args.limit]

    print(
        "PixelRAG GeoGuessr visual baseline"
    )
    print(
        f"API: {API_URL}"
    )
    print(
        f"Top-k: {TOP_K}"
    )
    print(
        f"Images to process: {len(records)}"
    )

    for index, record in enumerate(
        records,
        start=1,
    ):
        print(
            f"\n========== "
            f"{index}/{len(records)} "
            f"=========="
        )

        process_one(record)

    print(
        "\nBaseline query run complete."
    )
    print(
        f"Raw results: {RAW_RESULTS_PATH}"
    )
    print(
        f"Flattened hits: {HITS_PATH}"
    )


if __name__ == "__main__":
    main()