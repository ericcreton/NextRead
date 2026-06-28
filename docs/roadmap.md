# ML development roadmap

## 1. Working product foundation — implemented
React rating flow → FastAPI → SQL catalog → content/popularity ranking. Full metadata and genre import. Unit and API contract checks.

## 2. Reproducible evaluation — initial benchmark implemented
Import all six million ratings into a separate interaction table. Preserve row order and document the source's ordering claims; no explicit timestamps are supplied. Create seeded per-user train/validation/test splits with minimum-history rules and no duplicate user-book overlap. Compute popularity from training interactions only. Report Precision@10, Recall@10 and NDCG@10 for held-out ratings >=4, together with coverage and split statistics. Rank against all eligible unseen catalog items; document any negative sampling separately.

## 3. Collaborative filtering — initial SVD implemented
Train a regularized matrix-factorization model on training data. Save versioned factors, ID maps, training config and dataset checksums. Evaluate rating RMSE separately from retrieval metrics. Fit a new user's vector from their onboarding ratings; retain the content fallback for sparse profiles and unseen books.

## 4. Measured hybrid — initial validation blend implemented
Tune collaborative/content/popularity blend weights on validation data. Evaluate once against a frozen test set and compare to each component. Derive explanations from actual score contributions; avoid presenting ranking scores as calibrated ratings. Add author diversity and novelty only with measured tradeoffs.

## 5. Persistent product
Add authenticated profiles, server-side rating storage and to-read lists. Add database migrations, artifact loading, CI, deployment configuration and monitoring. Evaluate cold start by onboarding history size. Keep API recommendations and offline evaluation on the same scoring code.

## 6. Optional NLP extension
After a reliable benchmark, evaluate review-derived themes with a documented text source and licensing. Prevent review and interaction leakage into held-out data. Compare the incremental gain against the simpler content model.

## Current milestone

The first trained SVD and measured hybrid are live. See evaluation.md for results and limitations. Ratings are cached as CSV/arrays, not yet SQL interaction rows. Next: separately benchmark ten-rating onboarding, evaluate observed-only regularized matrix factorization against the frozen protocol with a fresh test holdout if retuning, add uncertainty estimates, and improve author diversity. The roadmap above includes remaining work beyond the initial implementation.
