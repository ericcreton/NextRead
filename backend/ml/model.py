"""Shared offline/online scoring. Artifacts contain arrays, never pickled code."""
import json
import numpy as np
from scipy import sparse
from sklearn.feature_extraction import DictVectorizer
from sklearn.preprocessing import normalize


def standardize(values):
    return (values - values.mean()) / max(float(values.std()), 1e-8)


def top_k(scores, excluded, k=10):
    scores = scores.copy()
    scores[list(excluded)] = -np.inf
    eligible = np.flatnonzero(np.isfinite(scores))
    return eligible[np.lexsort((eligible, -scores[eligible]))[:k]]


def ranking_metrics(ranked, relevant, k=10):
    hits = np.array([item in relevant for item in ranked[:k]], dtype=float)
    ideal = sum(1 / np.log2(np.arange(min(k, len(relevant))) + 2))
    return np.array([hits.sum() / k, hits.sum() / max(1, len(relevant)),
                     (hits / np.log2(np.arange(len(hits)) + 2)).sum() / max(ideal, 1e-12)])


class FactorModel:
    def __init__(self, ids, factors, popularity, content, alpha=.75, regularization=1.0):
        self.ids = np.asarray(ids)
        self.index = {int(bid): i for i, bid in enumerate(ids)}
        self.factors = factors
        self.popularity = popularity
        self.content = content
        self.alpha = float(alpha)
        self.regularization = regularization

    def components(self, ratings):
        pairs = [(self.index[bid], value - 3) for bid, value in ratings.items() if bid in self.index]
        if not pairs or not any(v for _, v in pairs):
            return self.popularity.copy(), self.popularity.copy(), False
        indices, values = zip(*pairs)
        vectors = self.factors[list(indices)]
        user = np.linalg.solve(vectors.T @ vectors + self.regularization * np.eye(vectors.shape[1]),
                               vectors.T @ np.array(values))
        collaborative = self.factors @ user
        profile = np.asarray(self.content[list(indices)].T @ np.array(values)).ravel()
        profile /= max(float(np.linalg.norm(profile)), 1e-8)
        content = np.asarray(self.content @ profile).ravel()
        return collaborative, content, True

    def scores(self, ratings, alpha=None):
        collaborative, content, personalized = self.components(ratings)
        if not personalized:
            return self.popularity.copy()
        weight = self.alpha if alpha is None else alpha
        return weight * standardize(collaborative) + (1 - weight) * standardize(content)

    def save(self, directory, metadata):
        directory.mkdir(parents=True, exist_ok=False)
        np.savez_compressed(directory / 'model.npz', ids=self.ids, factors=self.factors,
                            popularity=self.popularity, alpha=self.alpha, regularization=self.regularization)
        sparse.save_npz(directory / 'content.npz', self.content)
        (directory / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')

    @classmethod
    def load(cls, directory):
        with np.load(directory / 'model.npz', allow_pickle=False) as data:
            model = cls(data['ids'], data['factors'], data['popularity'], sparse.load_npz(directory / 'content.npz'),
                        float(data['alpha']), float(data['regularization']))
        if model.factors.shape[0] != len(model.ids) or model.content.shape[0] != len(model.ids):
            raise ValueError('Artifact dimensions do not match book IDs')
        if not np.isfinite(model.factors).all() or not np.isfinite(model.popularity).all():
            raise ValueError('Non-finite model values')
        return model


def content_matrix(books):
    features = [{**{f'genre:{g}': 1.0 for g in b['genres']},
                 **{f'author:{a.strip()}': 1.0 for a in b['authors'].split(',')}} for b in books]
    matrix = DictVectorizer(dtype=np.float32).fit_transform(features)
    frequency = np.asarray((matrix > 0).sum(axis=0)).ravel()
    matrix = matrix.multiply(np.log((1 + len(books)) / (1 + frequency)) + 1).tocsr()
    return normalize(matrix, copy=False)
