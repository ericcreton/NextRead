# First trained recommender benchmark

## Results

| Model | Precision@10 | Recall@10 | NDCG@10 | Catalog coverage |
|---|---:|---:|---:|---:|
| popularity | 0.0362 | 0.0499 | 0.0529 | 0.28% |
| content | 0.0600 | 0.0836 | 0.0880 | 23.71% |
| collaborative | 0.0263 | 0.0379 | 0.0381 | 3.67% |
| hybrid_0.25 | 0.0675 | 0.0933 | 0.0929 | 13.89% |

The hybrid improves NDCG@10 by about 5.5% relative to content-only in this sample. Standalone collaborative filtering underperforms: the learned factors help as a small additional signal, but do not justify replacing content similarity.

## Protocol

- Source: 5,976,479 Goodbooks-10k ratings from 53,424 users and 10,000 books.
- Seed 42; random split within each user. Training: 4,829,319; validation: 573,580; test: 573,580. No duplicate user-book pairs.
- All training ratings are used to learn factors. Evaluation samples 1,000 users deterministically; 997 have validation positives, and 995 have test positives. Users without positives are excluded from that split’s macro average.
- A relevant book is held out with rating 4 or 5. Rank all 10,000 catalog books except training history. No sampled negatives. Unobserved books and other held-out items count as non-relevant for the evaluated split.
- Popularity counts positive training interactions only; historical aggregate metadata ratings do not enter benchmark scoring.
- Content uses genres/authors and catalog-level IDF. Genre metadata is a full-catalog historical snapshot, not reconstructed at split time.
- The same training history is used to fit user vectors for validation and test. Neither validation nor test interactions enter fitting.
- Hybrid weights .25, .50, .75 were compared on validation NDCG@10. Selected .25 collaborative + .75 content, after per-user score standardization; then evaluated on test without retuning.

## Model and limits

Randomized truncated SVD learns 64 latent dimensions from a sparse matrix of rating minus 3. Seven power iterations and seed 42 are fixed. Item factors are right singular vectors scaled by square-root singular values. Online user factors solve regularized least squares with lambda 1 over known ratings. This is a ranking baseline, not an explicit-rating predictor optimized only over observed entries.

Missing entries and neutral ratings both become zero during SVD, a simplifying assumption that can weaken collaborative performance. Cold-start users with no non-neutral ratings receive training popularity; with ratings they use the same fold-in and blend as evaluation. Ten-rating onboarding has not been separately benchmarked.

The split is random, not a temporal forecast; unobserved books are not proven dislikes. Coverage describes the sampled recommendation lists. No confidence intervals or statistical-significance claims are provided. Do not repeatedly tune against this reported test set.

Reproduction: `uv run python scripts/train_model.py --factors 64 --eval-users 1000 --seed 42`.

Exact checksums, versions, evaluation user IDs, validation scores and configuration are in [evaluation.json](evaluation.json). Run artifacts and raw data are local and excluded from Git.

Algorithm reference: [scikit-learn TruncatedSVD](https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.TruncatedSVD.html). Dataset: [Goodbooks-10k](https://github.com/zygmuntz/goodbooks-10k).
