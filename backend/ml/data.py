import hashlib
import ssl
import urllib.request
import certifi
import numpy as np

SOURCE = 'https://raw.githubusercontent.com/zygmuntz/goodbooks-10k/master/ratings.csv'


def load_ratings(directory):
    path = directory / 'ratings.csv'
    if not path.exists():
        print('Downloading ratings.csv (~69 MB)...', flush=True)
        temp = path.with_suffix('.download')
        with urllib.request.urlopen(SOURCE, context=ssl.create_default_context(cafile=certifi.where()), timeout=120) as response, temp.open('wb') as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        temp.replace(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    print('Loading and validating ratings...', flush=True)
    data = np.loadtxt(path, delimiter=',', skiprows=1, dtype=np.int32)
    if data.ndim != 2 or data.shape[1] != 3 or np.any(data[:, :2] < 1) or np.any((data[:, 2] < 1) | (data[:, 2] > 5)):
        raise ValueError('Invalid ratings schema or values')
    keys = data[:, 0].astype(np.int64) * (int(data[:, 1].max()) + 1) + data[:, 1]
    if len(np.unique(keys)) != len(data):
        raise ValueError('Duplicate user-book interactions; refusing a potentially leaky split')
    return data, digest


def split_ratings(data, seed=42):
    """Seeded random 80/10/10 within each user; <10 interactions stay train-only."""
    rng = np.random.default_rng(seed)
    order = np.lexsort((rng.random(len(data)), data[:, 0]))
    sorted_users = data[order, 0]
    boundaries = np.r_[0, np.flatnonzero(np.diff(sorted_users)) + 1, len(data)]
    labels = np.zeros(len(data), dtype=np.uint8)
    for start, stop in zip(boundaries[:-1], boundaries[1:]):
        count = stop - start
        if count >= 10:
            holdout = max(1, count // 10)
            labels[order[start:start + holdout]] = 1
            labels[order[start + holdout:start + 2 * holdout]] = 2
    return labels
