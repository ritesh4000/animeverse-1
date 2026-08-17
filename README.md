# Animeverse

Animeverse is an anime discovery application with a FastAPI backend, a MySQL catalog, TF-IDF recommendations, an IMDb-inspired library, and AniList poster artwork.

## Features

- Browse and filter a 19,930-title anime catalog
- Search by title, genre, format, or studio
- View ratings, popularity, metadata, and details
- Discover hidden gems
- Generate content-based recommendations
- Load poster artwork from AniList with graceful fallbacks
- Run the complete stack with Docker Compose

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
db/                  MySQL schema, import script, and catalog CSV
docker-compose.yml   Local full-stack orchestration
.env.example         Environment variable template
```

## Data notice

Review `LICENSE_DATA_NOTICE.txt` before redistributing or using the included dataset commercially.

