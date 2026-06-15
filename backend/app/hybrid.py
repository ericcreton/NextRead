"""Online wrapper around the same factor scoring used in offline evaluation."""
import json
import logging
import os
from pathlib import Path
from backend.ml.model import FactorModel, top_k
from .db import ROOT
from .recommender import Recommender


class HybridRecommender(Recommender):
    def __init__(self, books, model, version):
        super().__init__(books)
        if set(self.books) != set(model.index):
            raise ValueError('Model/catalog book IDs differ; retrain the model')
        self.factor_model = model
        self.version = version

    def recommend(self, ratings, limit=12):
        base = super().recommend(ratings, len(self.books))
        explanations = {b['id']: b for b in base['books']}
        scores = self.factor_model.scores(ratings)
        excluded = [self.factor_model.index[bid] for bid in ratings]
        ranked = top_k(scores, excluded, limit)
        personalized = any(r != 3 for r in ratings.values())
        recommendations = []
        for index in ranked:
            book = explanations[int(self.factor_model.ids[index])]
            book['score'] = round(float(scores[index]), 5)
            if personalized:
                content_reason = book['reason'] if book['reason'].startswith('Matches') else ''
                book['reason'] = ('Ranked using patterns learned from reader ratings. ' + content_reason).strip()
            else:
                book['reason'] = 'Frequently rated 4 or 5 stars in the training data.'
            recommendations.append(book)
        return {**base, 'books': recommendations, 'method': 'hybrid-svd' if personalized else 'popularity',
                'model_version': self.version, 'collaborative_weight': self.factor_model.alpha}


def load_recommender(books):
    configured = os.getenv('NEXTREAD_MODEL_DIR')
    pointer = ROOT / 'data' / 'models' / 'current.json'
    if not configured and not pointer.exists():
        return Recommender(books)
    try:
        directory = Path(configured) if configured else pointer.parent / json.loads(pointer.read_text())['run']
        return HybridRecommender(books, FactorModel.load(directory), directory.name)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        logging.getLogger(__name__).warning('Model unavailable; using content fallback: %s', exc)
        return Recommender(books)
