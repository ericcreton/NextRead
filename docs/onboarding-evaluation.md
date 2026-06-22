# New-reader and discovery audit

Reproduce: `uv run python scripts/evaluate_onboarding.py` after training.

| Ratings | Popularity NDCG@10 | Content | Hybrid | Discovery | Authors: hybrid → discovery |
|---|---:|---:|---:|---:|---:|
| 5 | .0580 | .0576 | .0809 | .0800 | 4.65 → 7.94 |
| 10 | .0580 | .0608 | .0921 | .0922 | 4.99 → 7.96 |
| 20 | .0580 | .0683 | .0990 | .0949 | 5.74 → 8.29 |

## Protocol

Independently refit 64-factor SVD after removing **all training interactions** belonging to 500 audit readers. Training popularity also excludes these readers. This audit never replaces production artifacts. Reader selection uses seed 2026, at least 20 available training ratings, and excludes readers from the original evaluation. Item splitting remains seed 42. All 500 sampled readers have relevant test books.

The fixed .25 collaborative blend is reused without tuning. Nested deterministic samples supply 5, 10 or 20 historical ratings per reader. Targets are unchanged test ratings >=4. Rank the full catalog except each reader's complete training history; no sampled negatives. Unobserved items count as non-relevant.

Excluding complete training histories prevents hidden already-read books from counting as false positives, but gives candidate filtering more information than the app actually has. These are active readers simulated as new users, using random onboarding choices. The audit does not measure real users choosing their favorite books. Metadata is a full-catalog historical snapshot. Results cannot be compared directly to the earlier benchmark with a different training population.

## Discovery tradeoff

The shared API/audit policy keeps at most two books per primary author and one per parsed series and skips title-detected bundles. Title matching is heuristic; it does not infer reading order or identify every edition.

At ten ratings, discovery changes NDCG by +.00012. The paired bootstrap 95% interval is approximately [-.00589, +.00613], which does not establish an accuracy gain or equivalence. The observed benefit is author variety. At twenty ratings, observed NDCG drops from .0990 to .0949.

Catalog coverage falls at every profile size: greater author variety within each list does not imply broader coverage across readers. Bootstrap intervals cover sampled-reader uncertainty, not retraining randomness or selection bias. Policies were fixed before this audit; do not repeatedly tune against its test outcomes.

Exact metrics, intervals and selected reader IDs: [onboarding-evaluation.json](onboarding-evaluation.json).
