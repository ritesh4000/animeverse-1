# Animeverse

Animeverse is a free, static anime discovery site with an IMDb-inspired library, TF-IDF recommendations, and AniList poster artwork.

## Live site

[Open Animeverse on GitHub Pages](https://Shraa243.github.io/animeverse-1/)

## Features

- Browse and filter a 19,930-title anime catalog
- Search by title, genre, format, or studio
- View ratings, popularity, metadata, and details
- Discover hidden gems
- Generate content-based recommendations
- Load poster artwork from AniList with graceful fallbacks
- Run entirely in the browser from GitHub Pages

The public site does not need FastAPI, MySQL, or a paid server. Its catalog and
recommendations are precomputed as JSON files in `app/static/data`. Poster images
are requested from AniList when a visitor opens the site, so internet access is
still required for artwork.

## GitHub Pages deployment

Every push to `main` deploys `app/static` through
`.github/workflows/pages.yml`.

To rebuild the browser data after changing `db/anime.csv`:

```bash
python -m pip install numpy scikit-learn
python scripts/build_static_data.py
```

Commit the regenerated files in `app/static/data` and push them to `main`.

## Run with Docker

1. Install Docker Desktop.
2. Copy `.env.example` to `.env`.
3. Replace the placeholder passwords in `.env`.
4. Start the application:

   ```bash
   docker compose up --build
   ```

5. Open `http://localhost:8000`.

The first startup creates the MySQL schema and imports the included catalog.

## Project structure

```text
app/                 FastAPI application and frontend
app/static/data/     Browser-ready catalog and recommendation data
db/                  MySQL schema, import script, and catalog CSV
docker-compose.yml   Local full-stack orchestration
scripts/             Static data build tools
.github/workflows/   GitHub Pages deployment workflow
.env.example         Environment variable template
```

## Data notice

Review `LICENSE_DATA_NOTICE.txt` before redistributing or using the included dataset commercially.
