from __future__ import annotations

import argparse
import csv
import random
import re
import subprocess
from collections import defaultdict
from pathlib import Path


DATASET = "ubitquitin/geolocation-geoguessr-images-50k"
PAGE_SIZE = 1000
N_COUNTRIES = 30
IMAGES_PER_COUNTRY = 5
SEED = 42

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
MANIFEST_PATH = DATA_DIR / "kaggle_file_manifest.csv"
PLAN_PATH = DATA_DIR / "sample_plan.csv"
METADATA_PATH = DATA_DIR / "eval_metadata.csv"
IMAGE_DIR = DATA_DIR / "images"
DOWNLOAD_TMP_DIR = DATA_DIR / "_kaggle_downloads"


def run_kaggle(args: list[str]) -> str:
    command = ["kaggle", *args]

    print("\n$", " ".join(command))

    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise RuntimeError(
            f"Kaggle command failed with exit code {result.returncode}"
        )

    return result.stdout


def parse_page(output: str) -> tuple[list[dict], str | None]:
    """Parse one `kaggle datasets files` page."""

    next_token = None

    token_match = re.search(
        r"Next Page Token\s*=\s*(\S+)",
        output,
    )

    if token_match:
        next_token = token_match.group(1)

    records = []

    for raw_line in output.splitlines():
        line = raw_line.strip()

        if not line.startswith("compressed_dataset/"):
            continue

        # Handles country names containing spaces, e.g.
        # compressed_dataset/American Samoa/...
        match = re.match(
            r"^(compressed_dataset/.+?\.(?:jpg|jpeg|png|webp))\s+\d+\s+",
            line,
            re.IGNORECASE,
        )

        if not match:
            continue

        source_path = match.group(1)

        parts = Path(source_path).parts

        if len(parts) < 3:
            continue

        country = parts[1]
        filename = parts[-1]

        records.append(
            {
                "source_path": source_path,
                "country": country,
                "filename": filename,
            }
        )

    return records, next_token


def build_full_manifest() -> list[dict]:
    """Walk every Kaggle pagination page."""

    print("Building complete Kaggle file manifest...")
    print(f"Dataset: {DATASET}")
    print(f"Page size: {PAGE_SIZE}")

    all_records = []
    token = None
    seen_tokens = set()
    page_number = 0

    while True:
        page_number += 1

        args = [
            "datasets",
            "files",
            DATASET,
            "--page-size",
            str(PAGE_SIZE),
        ]

        if token:
            args.extend(["--page-token", token])

        output = run_kaggle(args)

        records, next_token = parse_page(output)

        all_records.extend(records)

        print(
            f"Page {page_number}: "
            f"{len(records)} image files found | "
            f"total so far: {len(all_records)}"
        )

        if not next_token:
            break

        if next_token in seen_tokens:
            raise RuntimeError(
                "Kaggle returned a repeated page token. "
                "Stopping to avoid an infinite loop."
            )

        seen_tokens.add(next_token)
        token = next_token

    # Remove accidental duplicates while preserving order.
    unique = {}
    for record in all_records:
        unique[record["source_path"]] = record

    all_records = list(unique.values())

    print(
        f"\nComplete manifest: {len(all_records)} unique image files"
    )

    return all_records


def save_manifest(records: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with MANIFEST_PATH.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "source_path",
                "country",
                "filename",
            ],
        )
        writer.writeheader()
        writer.writerows(records)

    print(f"Saved manifest: {MANIFEST_PATH}")


def load_manifest() -> list[dict]:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(
            f"Manifest not found: {MANIFEST_PATH}"
        )

    with MANIFEST_PATH.open(
        newline="",
        encoding="utf-8",
    ) as f:
        return list(csv.DictReader(f))


def create_sample_plan(records: list[dict]) -> list[dict]:
    by_country = defaultdict(list)

    for record in records:
        by_country[record["country"]].append(record)

    eligible = {
        country: files
        for country, files in by_country.items()
        if len(files) >= IMAGES_PER_COUNTRY
    }

    print(
        f"Countries in dataset: {len(by_country)}"
    )
    print(
        f"Countries with >= {IMAGES_PER_COUNTRY} images: "
        f"{len(eligible)}"
    )

    if len(eligible) < N_COUNTRIES:
        raise RuntimeError(
            f"Only {len(eligible)} countries have enough images; "
            f"{N_COUNTRIES} required."
        )

    rng = random.Random(SEED)

    selected_countries = sorted(
        rng.sample(
            sorted(eligible.keys()),
            N_COUNTRIES,
        )
    )

    print("\nFrozen country sample:")

    plan = []
    image_number = 1

    for country in selected_countries:
        selected_files = rng.sample(
            eligible[country],
            IMAGES_PER_COUNTRY,
        )

        print(
            f"  {country}: "
            f"{IMAGES_PER_COUNTRY} images"
        )

        for record in selected_files:
            plan.append(
                {
                    "image_id": f"geo_{image_number:04d}",
                    "country": country,
                    "source_path": record["source_path"],
                    "source_filename": record["filename"],
                    "split": "frozen_eval",
                }
            )

            image_number += 1

    with PLAN_PATH.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "image_id",
                "country",
                "source_path",
                "source_filename",
                "split",
            ],
        )
        writer.writeheader()
        writer.writerows(plan)

    print(
        f"\nSaved frozen sample plan: {PLAN_PATH}"
    )
    print(
        f"Total images selected: {len(plan)}"
    )

    return plan


def download_file(source_path: str, image_id: str) -> Path:
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_TMP_DIR.mkdir(parents=True, exist_ok=True)

    destination = IMAGE_DIR / f"{image_id}.jpg"

    if destination.exists() and destination.stat().st_size > 0:
        print(f"Already exists: {destination.name}")
        return destination

    filename = Path(source_path).name
    temporary_file = DOWNLOAD_TMP_DIR / filename

    if not temporary_file.exists():
        run_kaggle(
            [
                "datasets",
                "download",
                DATASET,
                "-f",
                source_path,
                "-p",
                str(DOWNLOAD_TMP_DIR),
            ]
        )

    if not temporary_file.exists():
        raise FileNotFoundError(
            f"Expected downloaded file was not found: "
            f"{temporary_file}"
        )

    temporary_file.replace(destination)

    print(
        f"Downloaded {image_id}: "
        f"{destination.name}"
    )

    return destination


def download_plan(plan: list[dict]) -> None:
    print(
        f"\nDownloading {len(plan)} frozen evaluation images..."
    )

    successful = 0

    for index, record in enumerate(plan, start=1):
        print(
            f"\n[{index}/{len(plan)}] "
            f"{record['image_id']} "
            f"({record['country']})"
        )

        try:
            download_file(
                record["source_path"],
                record["image_id"],
            )
            successful += 1

        except Exception as exc:
            print(
                f"ERROR downloading "
                f"{record['image_id']}: {exc}"
            )
            raise

    print(
        f"\nSuccessfully downloaded: "
        f"{successful}/{len(plan)}"
    )


def create_eval_metadata(plan: list[dict]) -> None:
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    with METADATA_PATH.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "image_id",
                "image_path",
                "country",
                "city_region",
                "split",
                "useful_visible_text",
            ],
        )

        writer.writeheader()

        for record in plan:
            image_path = IMAGE_DIR / f"{record['image_id']}.jpg"

            writer.writerow(
                {
                    "image_id": record["image_id"],
                    "image_path": str(
                        image_path.relative_to(ROOT)
                    ).replace("\\", "/"),
                    "country": record["country"],
                    "city_region": "",
                    "split": record["split"],
                    "useful_visible_text": "",
                }
            )

    print(
        f"Saved evaluation metadata: {METADATA_PATH}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare frozen GeoGuessr evaluation dataset."
    )

    parser.add_argument(
        "--plan",
        action="store_true",
        help="Build complete manifest and frozen sample plan.",
    )

    parser.add_argument(
        "--download",
        action="store_true",
        help="Download the already-created frozen sample.",
    )

    args = parser.parse_args()

    if not args.plan and not args.download:
        parser.error(
            "Choose --plan or --download."
        )

    if args.plan:
        records = build_full_manifest()
        save_manifest(records)
        create_sample_plan(records)

    if args.download:
        plan = load_sample_plan()
        download_plan(plan)
        create_eval_metadata(plan)


def load_sample_plan() -> list[dict]:
    if not PLAN_PATH.exists():
        raise FileNotFoundError(
            f"Sample plan not found: {PLAN_PATH}\n"
            "Run --plan first."
        )

    with PLAN_PATH.open(
        newline="",
        encoding="utf-8",
    ) as f:
        return list(csv.DictReader(f))


if __name__ == "__main__":
    main()