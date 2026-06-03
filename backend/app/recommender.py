"""Content cosine similarity + Bayesian popularity; no trained rating predictor."""
import math
from collections import Counter

class Recommender:
    def __init__(self, books):
        self.books = {b['id']: b for b in books}
        features = {b['id']: Counter([f'genre:{g}' for g in b['genres']] +
                    [f'author:{a.strip()}' for a in b['authors'].split(',')]) for b in books}
        document_frequency = Counter(f for fs in features.values() for f in fs)
        self.vectors = {}
        for bid, fs in features.items():
            vec = {f: count * (math.log((1 + len(books)) / (1 + document_frequency[f])) + 1) for f, count in fs.items()}
            norm = math.sqrt(sum(v*v for v in vec.values())) or 1
            self.vectors[bid] = {f: v / norm for f, v in vec.items()}
        self.mean = sum(b['average_rating'] for b in books) / max(len(books), 1)

    def recommend(self, ratings, limit=12):
        profile = Counter()
        for bid, rating in ratings.items():
            for feature, value in self.vectors.get(bid, {}).items():
                profile[feature] += (rating - 3) * value
        norm = math.sqrt(sum(v*v for v in profile.values())) or 1
        profile = {f: v / norm for f, v in profile.items()}
        personalized = any(v != 0 for v in profile.values())
        results = []
        for bid, book in self.books.items():
            if bid in ratings:
                continue
            similarity = sum(profile.get(f, 0) * v for f, v in self.vectors[bid].items())
            n = book['ratings_count']
            popularity = (n * book['average_rating'] + 10000 * self.mean) / (n + 10000) / 5
            score = .8 * similarity + .2 * popularity if personalized else popularity
            matches = sorted(((profile.get(f, 0) * v, f) for f, v in self.vectors[bid].items() if profile.get(f, 0) > 0), reverse=True)
            reasons = [f.split(':', 1)[1] for _, f in matches[:2]]
            reason = 'Matches your interest in ' + ' and '.join(reasons) + '.' if reasons else 'A highly rated book to help you explore.'
            results.append({**book, 'score': round(score, 4), 'reason': reason})
        results.sort(key=lambda b: (-b['score'], b['id']))
        genres = sorted(((f[6:], v) for f, v in profile.items() if f.startswith('genre:') and v > 0), key=lambda p: -p[1])[:5]
        peak = max((v for _, v in genres), default=1)
        return {'books': results[:limit], 'profile': [{'genre': g, 'strength': round(v / peak * 100)} for g, v in genres],
                'method': 'content-popularity' if personalized else 'popularity', 'rated_count': len(ratings)}
