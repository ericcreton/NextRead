# Reproduce from a clean checkout

Requirements: Git, Python 3.12, uv, Node 24 and npm. Install uv using https://docs.astral.sh/uv/getting-started/installation/ if needed.

Clone the repository, then run:

```sh
git clone https://github.com/ericcreton/NextRead.git
cd NextRead
uv sync --locked --extra dev
uv run pytest -q
npm --prefix frontend ci
npm --prefix frontend run build
uv run python scripts/import_goodbooks.py
uv run python scripts/train_model.py --factors 64 --eval-users 1000 --seed 42
uv run python scripts/evaluate_onboarding.py
uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8001
```

In another terminal run `npm --prefix frontend run dev` and open http://127.0.0.1:5173. Check http://127.0.0.1:8001/api/health for the loaded model version. The server loads artifacts at startup, so restart after training.

Downloads require network access and disk space for the CSVs, SQLite database and training arrays. No API keys are required. SQLite is the default; optional PostgreSQL setup is in README.md. Tests and CI do not require downloaded data or model artifacts.

The training command writes a new local version under data/models/ and updates the local current.json pointer. It regenerates docs/evaluation.json; the onboarding command regenerates docs/onboarding-evaluation.json. Metric values can differ slightly across numerical libraries/platforms. Markdown reports describe the recorded reference runs and are not automatically rewritten; compare the regenerated JSON before updating claims.

No raw datasets or model arrays should be committed. Check `git status --short --ignored data/` before publishing. See DATA_ATTRIBUTION.md for source and license details.
