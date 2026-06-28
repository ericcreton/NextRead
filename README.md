# NextRead

[![Checks](https://github.com/ericcreton/NextRead/actions/workflows/checks.yml/badge.svg)](https://github.com/ericcreton/NextRead/actions/workflows/checks.yml)

A book discovery app built around Goodbooks-10k. Rate books, see your genre affinities, and explore recommendations with explanations.

## Run locally

Python 3.11+ and Node 20.19+ (or 22.12+) are required.

```sh
uv sync --locked --extra dev
uv run python scripts/import_goodbooks.py
uv run uvicorn backend.app.main:app --reload --port 8001
```

In a second terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5173. API documentation is at http://127.0.0.1:8001/docs.
The importer downloads three source CSVs, imports 10,000 books, and can be rerun safely. Restart the API after import. Raw data and the local database are ignored by Git.

SQLite is the default for a quick start. For PostgreSQL, run `docker compose up -d`, then export the `DATABASE_URL` shown in `.env.example` in the shell used for both import and API startup. The app does not automatically load `.env` files. Docker credentials are for local development only.

## What works today

- Search and paginate the full catalog. Browser-local ratings support adding, changing, and removing preferences.
- Train a 64-factor collaborative SVD model on 4.83 million training ratings. Fold new readers into the learned space with a regularized least-squares solve.
- Blend standardized collaborative scores with TF-IDF genre/author similarity, using a weight selected on validation NDCG@10.
- Exclude rated books and display explanations. Ranking scores are not predicted star ratings; the displayed stars are historical community averages.
- Load a versioned local model at API startup. If artifacts are absent or unreadable, log the issue and fall back to the original content/popularity baseline. `/api/health` reports the loaded model version.
- Use original typographic book-cover treatments, not publisher artwork.

## Train and evaluate

After importing the catalog:

```sh
uv run python scripts/train_model.py --factors 64 --eval-users 1000 --seed 42
```

This downloads about 69 MB of ratings, validates IDs and uniqueness, saves a seeded per-user split, trains on the training partition only, selects a blend on validation data, then evaluates the frozen blend on test data. It writes immutable run directories under `data/models/`, a `current.json` pointer, and `docs/evaluation.json`. Restart the API to load the new run. Set `NEXTREAD_MODEL_DIR` to an existing run directory to pin or roll back a model.

The API and benchmark share `backend/ml/model.py`. Artifacts use NumPy/SciPy arrays with pickle disabled, and contain book-ID mappings, factors, content vectors, training-only popularity, hyperparameters and checksums. The installed versions are pinned in `uv.lock`.

Ratings are cached in CSV and split arrays for sparse training; **the six million interaction rows are not yet imported into PostgreSQL**. The SQL database currently holds the catalog. Reader ratings remain in browser storage and are sent to the API for scoring; there are no accounts or server-side personal histories yet.

See [the measured evaluation report](docs/evaluation.md). Results are a random-holdout benchmark on sampled existing users, not proof of performance for new readers with only ten ratings. The API remains a local development service.

## Checks

```sh
uv run pytest
cd frontend
npm run build
```

## Data provenance

Source: [Goodbooks-10k by Zygmunt Zając](https://github.com/zygmuntz/goodbooks-10k), licensed under [Creative Commons Attribution-ShareAlike 4.0](https://creativecommons.org/licenses/by-sa/4.0/). See [dataset attribution](DATA_ATTRIBUTION.md) for the source, transformations, and license scope. Raw data and model arrays are regenerated locally and are not distributed in this repository.

`books.book_id` is the key for ratings; tag rows join through `books.goodreads_book_id`. The importer keeps the five most common tags from an explicit genre allowlist and drops shelf-state labels such as “to-read.” Author strings are split on commas; contributor role disambiguation remains future work. Goodreads metadata is a historical snapshot, not a current catalog.

See [the roadmap](docs/roadmap.md) for the ML milestones.

## New-reader audit and discovery

Run `uv run python scripts/evaluate_onboarding.py` after training to reproduce the [onboarding audit](docs/onboarding-evaluation.md). It trains an independent audit model excluding 500 readers entirely, compares 5/10/20-rating profiles, and does not change the production model.

The UI enables **More variety** by default in Your next reads; turn it off for score-only ranking. The API accepts `diverse: true` (default false for backwards compatibility). Discovery limits primary-author and parsed-series repetition and skips title-detected bundles. A small candidate set can return fewer results than requested. These are heuristics, not definitive edition/series metadata.

GitHub Actions checks backend tests and the frontend build without downloaded data or trained models. Both jobs have passed on GitHub Actions.

For a fresh setup, see [reproduction instructions](docs/reproduce.md).
