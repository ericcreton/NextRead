"""Reproducible full-data SVD training, validation selection, and held-out evaluation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import sklearn
from scipy import sparse
from sklearn.decomposition import TruncatedSVD
from threadpoolctl import threadpool_limits
from sqlalchemy import select
from backend.app.db import Book, ROOT, Session, serialize
from backend.ml.data import load_ratings, split_ratings, SOURCE
from backend.ml.model import FactorModel, content_matrix, ranking_metrics, standardize, top_k


def evaluate(model, train, heldout, users, weights):
    names = ['popularity', 'content', 'collaborative'] + [f'hybrid_{w}' for w in weights]
    totals = {n: np.zeros(3) for n in names}
    coverage = {n: set() for n in names}
    evaluated = 0
    for user in users:
        history = train.getrow(user)
        target = heldout.getrow(user)
        relevant = set(target.indices[target.data >= 4])
        if not relevant:
            continue
        ratings = {int(model.ids[i]): int(v) for i, v in zip(history.indices, history.data)}
        cf, content, _ = model.components(ratings)
        scores = {'popularity': model.popularity, 'content': content, 'collaborative': cf}
        for w in weights:
            scores[f'hybrid_{w}'] = w * standardize(cf) + (1 - w) * standardize(content)
        for name, values in scores.items():
            ranked = top_k(values, history.indices)
            totals[name] += ranking_metrics(ranked, relevant)
            coverage[name].update(ranked.tolist())
        evaluated += 1
    if not evaluated:
        raise ValueError('No evaluation users have relevant held-out books')
    return {n: dict(zip(['precision@10', 'recall@10', 'ndcg@10'], (totals[n] / evaluated).tolist()),
                    coverage=len(coverage[n]) / len(model.ids), users=evaluated) for n in names}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--factors', type=int, default=64)
    parser.add_argument('--eval-users', type=int, default=1000)
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    if args.factors < 1 or args.eval_users < 1:
        parser.error('factors and eval-users must be positive')
    started = time.time()
    data, checksum = load_ratings(ROOT / 'data')
    with Session() as session:
        books = [serialize(b) for b in session.scalars(select(Book).order_by(Book.id))]
    ids = np.array([b['id'] for b in books])
    if not len(ids) or not np.isin(data[:, 1], ids).all():
        raise ValueError('Import the full catalog before training')
    items = np.searchsorted(ids, data[:, 1])
    users = data[:, 0] - 1
    shape = (int(users.max()) + 1, len(ids))
    labels = split_ratings(data, args.seed)
    split_path = ROOT / 'data' / f'split-{args.seed}-{checksum[:12]}.npz'
    np.savez_compressed(split_path, labels=labels)
    matrices = [sparse.csr_matrix((data[labels == part, 2].astype(np.float32),
                 (users[labels == part], items[labels == part])), shape=shape) for part in range(3)]
    train, validation, test = matrices
    preferences = train.copy()
    preferences.data -= 3
    preferences.eliminate_zeros()
    print(f'Training {args.factors}-factor SVD on {train.nnz:,} training ratings...', flush=True)
    svd = TruncatedSVD(n_components=args.factors, n_iter=7, random_state=args.seed)
    svd.fit(preferences)
    factors = svd.components_.T * np.sqrt(svd.singular_values_)
    positive = train.copy()
    positive.data = (positive.data >= 4).astype(np.float32)
    popularity = np.asarray(positive.sum(axis=0)).ravel()
    model = FactorModel(ids, factors, popularity, content_matrix(books))
    eligible = np.flatnonzero((np.diff(train.indptr) >= 8) & (np.diff(validation.indptr) > 0) & (np.diff(test.indptr) > 0))
    selected = np.random.default_rng(args.seed).choice(eligible, min(args.eval_users, len(eligible)), replace=False)
    weights = [.25, .5, .75]
    print(f'Validating on {len(selected):,} users against all {len(ids):,} books...', flush=True)
    valid = evaluate(model, train, validation, selected, weights)
    alpha = max(weights, key=lambda w: valid[f'hybrid_{w}']['ndcg@10'])
    model.alpha = alpha
    print(f'Frozen hybrid weight: {alpha}. Evaluating test set...', flush=True)
    final = evaluate(model, train, test, selected, [alpha])
    metadata = {'schema_version': 1, 'algorithm': 'signed-preference-truncated-svd', 'seed': args.seed,
                'factors': args.factors, 'svd_iterations': 7, 'regularization': model.regularization,
                'sklearn_version': sklearn.__version__, 'source': SOURCE, 'ratings_sha256': checksum,
                'catalog_sha256': hashlib.sha256(json.dumps(books, sort_keys=True).encode()).hexdigest(),
                'interactions': len(data), 'users': shape[0], 'books': len(ids),
                'split_counts': dict(zip(['train', 'validation', 'test'], [m.nnz for m in matrices])),
                'split': 'seeded random per-user 80/10/10; users with <10 ratings train-only',
                'split_labels_sha256': hashlib.sha256(labels.tobytes()).hexdigest(),
                'evaluation_user_ids': (selected + 1).tolist(), 'alpha': alpha,
                'validation': valid, 'test': final, 'seconds': round(time.time() - started, 2),
                'protocol': 'Relevance >=4. All catalog candidates except training history; unobserved items treated as non-relevant. Validation/test ratings are never folded in. Macro averages over sampled users with positives in that split.',
                'limitations': ['Random holdout, not temporal forecasting.', 'Metadata tags are a full-catalog historical snapshot.', 'Missing entries and neutral ratings both become zero in SVD.', 'Ranking scores are not predicted star ratings.', 'Evaluation sample is not all users; no uncertainty intervals.', 'Hybrid alpha chosen among .25/.5/.75, not a guarantee it beats pure collaborative.']}
    run = f'svd-{time.strftime("%Y%m%d-%H%M%S")}-{checksum[:8]}'
    directory = ROOT / 'data' / 'models' / run
    model.save(directory, metadata)
    report = ROOT / 'docs' / 'evaluation.json'
    report.write_text(json.dumps(metadata, indent=2) + '\n')
    pointer = ROOT / 'data' / 'models' / 'current.json'
    temp = pointer.with_suffix('.tmp')
    temp.write_text(json.dumps({'run': run}))
    temp.replace(pointer)
    print(json.dumps({'artifact': str(directory), 'test': final, 'seconds': metadata['seconds']}, indent=2), flush=True)

if __name__ == '__main__':
    with threadpool_limits(limits=1):
        main()
