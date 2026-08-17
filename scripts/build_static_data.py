"""Build the browser-ready Animeverse catalog and recommendation files."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "db" / "anime.csv"
OUTPUT = ROOT / "app" / "static" / "data"
TOP_K = 30
CHUNK_SIZE = 256


def integer(value: str) -> int | None:
    try:
        return int(float(value)) if value.strip() else None
    except (TypeError, ValueError):
        return None


def decimal(value: str) -> float | None:
    try:
        return round(float(value), 2) if value.strip() else None
    except (TypeError, ValueError):
        return None


def compact_json(path: Path, value: object) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, separators=(",", ":"))


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with SOURCE.open(encoding="utf-8-sig", newline="") as handle:
        source_rows = list(csv.DictReader(handle))

    catalog = []
    features = []
    genres: set[str] = set()
    studios: set[str] = set()
    types: set[str] = set()

    for anime_id, row in enumerate(source_rows, start=1):
        genre_text = (row.get("genres") or "").strip()
        studio_text = (row.get("studios") or "").strip()
        anime_type = (row.get("type") or "").strip()
        genres.update(part.strip() for part in genre_text.split(",") if part.strip())
        studios.update(part.strip() for part in studio_text.split(",") if part.strip())
        if anime_type:
            types.add(anime_type)

        catalog.append(
            {
                "id": anime_id,
                "name": (row.get("name") or "Untitled").strip(),
                "score": decimal(row.get("score") or ""),
                "popularity": integer(row.get("popularity") or ""),
                "genres": genre_text,
                "studios": studio_text,
                "type": anime_type,
                "year": integer(row.get("year") or ""),
                "episodes": integer(row.get("episodes") or ""),
                "themes": (row.get("themes") or "").strip(),
                "demographic": (row.get("demographic") or "").strip(),
                "synopsis": (row.get("synopsis") or "").strip(),
            }
        )
        features.append((row.get("features") or "").strip())

    print(f"Loaded {len(catalog):,} titles; creating TF-IDF matrix...", flush=True)
    vectorizer = TfidfVectorizer(
        stop_words="english", ngram_range=(1, 2), min_df=1, dtype=np.float32
    )
    matrix = vectorizer.fit_transform(features)
    recommendations: dict[str, list[list[int | float]]] = {}

    for start in range(0, len(catalog), CHUNK_SIZE):
        end = min(start + CHUNK_SIZE, len(catalog))
        similarities = (matrix[start:end] @ matrix.T).toarray()
        for local_index, row_scores in enumerate(similarities):
            source_index = start + local_index
            row_scores[source_index] = -1
            candidates = np.argpartition(row_scores, -TOP_K)[-TOP_K:]
            ordered = candidates[np.argsort(row_scores[candidates])[::-1]]
            recommendations[str(source_index + 1)] = [
                [int(candidate + 1), round(float(row_scores[candidate]), 4)]
                for candidate in ordered
            ]
        if start == 0 or end == len(catalog) or end % 2048 == 0:
            print(f"Recommendations: {end:,}/{len(catalog):,}", flush=True)

    hidden_gems = [
        item["id"]
        for item in sorted(
            (
                item
                for item in catalog
                if item["score"] is not None
                and item["popularity"] is not None
                and item["score"] >= 7.5
            ),
            key=lambda item: (-item["score"], -item["popularity"]),
        )[:12]
    ]
    meta = {
        "stats": {
            "total_anime": len(catalog),
            "studios": len(studios),
            "genres": len(genres),
        },
        "genres": sorted(genres),
        "types": sorted(types),
        "hidden_gems": hidden_gems,
    }

    compact_json(OUTPUT / "catalog.json", catalog)
    compact_json(OUTPUT / "meta.json", meta)
    compact_json(OUTPUT / "recommendations.json", recommendations)
    print("Static data written to app/static/data", flush=True)


if __name__ == "__main__":
    main()
