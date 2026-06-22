"""New-user audit. Fixed policy; no tuning or replacement of production artifacts."""
import sys
import json
import hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from scipy import sparse
from sklearn.decomposition import TruncatedSVD
from sqlalchemy import select
from threadpoolctl import threadpool_limits
from backend.app.db import ROOT, Session, Book, serialize
from backend.ml.data import load_ratings, split_ratings
from backend.ml.model import FactorModel, content_matrix, top_k, ranking_metrics
from backend.ml.ranking import diversify, author_key


def bootstrap_delta(values, seed=2026):
    rng = np.random.default_rng(seed)
    means = [rng.choice(values, len(values), replace=True).mean() for _ in range(2000)]
    return np.quantile(means, [.025, .975]).tolist()


def main():
    data, checksum = load_ratings(ROOT / 'data')
    source = json.loads((ROOT / 'docs/evaluation.json').read_text())
    if checksum != source['ratings_sha256']:
        raise ValueError('Ratings do not match original experiment')
    with Session() as session:
        books = [serialize(b) for b in session.scalars(select(Book).order_by(Book.id))]
    ids = np.array([b['id'] for b in books])
    if not np.isin(data[:,1], ids).all():
        raise ValueError('Catalog does not cover ratings')
    labels = split_ratings(data, source['seed'])
    shape = (int(data[:,0].max()), len(ids))
    items = np.searchsorted(ids, data[:,1])
    train = sparse.csr_matrix((data[labels==0,2].astype(np.float32), (data[labels==0,0]-1, items[labels==0])),shape=shape)
    test = sparse.csr_matrix((data[labels==2,2].astype(np.float32), (data[labels==2,0]-1, items[labels==2])),shape=shape)
    eligible = np.flatnonzero(np.diff(train.indptr)>=20)
    # Avoid the readers used to choose the original blend, as well as their test sample.
    eligible = np.setdiff1d(eligible, np.array(source['evaluation_user_ids'])-1)
    selected = np.random.default_rng(2026).choice(eligible, min(500,len(eligible)),replace=False)
    fitting = train.copy()
    for u in selected:
        fitting.data[fitting.indptr[u]:fitting.indptr[u+1]]=0
    fitting.eliminate_zeros()
    assert all(fitting.getrow(u).nnz == 0 for u in selected)
    preferences = fitting.copy()
    preferences.data -= 3
    preferences.eliminate_zeros()
    print('Fitting independent audit factors with all audit readers excluded...',flush=True)
    svd=TruncatedSVD(n_components=64,n_iter=7,random_state=42).fit(preferences)
    positives=fitting.copy()
    positives.data=(positives.data>=4).astype(np.float32)
    model=FactorModel(ids,svd.components_.T*np.sqrt(svd.singular_values_),np.asarray(positives.sum(axis=0)).ravel(),content_matrix(books),alpha=source['alpha'])
    report={'seed':2026,'ratings_sha256':checksum,'production_model_changed':False,'training_interactions':fitting.nnz,'excluded_user_ids':(selected+1).tolist(),'alpha':model.alpha,'results':{}}
    for size in [5,10,20]:
        metrics={n:[] for n in ['popularity','content','hybrid','discovery']}
        diversity={n:[] for n in metrics}
        coverage={n:set() for n in metrics}
        for u in selected:
            target=test.getrow(u)
            relevant=set(target.indices[target.data>=4])
            if not relevant:
                continue
            history=train.getrow(u)
            order=np.random.default_rng(2026+int(u)).permutation(len(history.indices))[:size]
            ratings={int(ids[history.indices[i]]):int(history.data[i]) for i in order}
            scores=model.scores(ratings)
            # Exclude the full known training history so hidden read books do not
            # become false negatives. Only the selected subset contributes scores.
            excluded=history.indices
            hybrid=top_k(scores,excluded,len(ids))
            varied=diversify([books[i] for i in hybrid],10)
            rankings={'popularity':top_k(model.popularity,excluded),
                      'content':top_k(model.scores(ratings,alpha=0),excluded),
                      'hybrid':hybrid[:10], 'discovery':np.array([model.index[b['id']] for b in varied])}
            for name, ranked in rankings.items():
                metrics[name].append(ranking_metrics(ranked,relevant))
                diversity[name].append(len({author_key(books[i]) for i in ranked}))
                coverage[name].update(ranked.tolist())
        rows={}
        for name, values in metrics.items():
            rows[name]=dict(zip(['precision@10','recall@10','ndcg@10'],np.mean(values,axis=0).tolist()),
                            users=len(values),unique_authors_at_10=float(np.mean(diversity[name])),coverage=len(coverage[name])/len(ids))
        delta=np.array(metrics['discovery'])[:,2]-np.array(metrics['hybrid'])[:,2]
        rows['discovery_minus_hybrid_ndcg_95ci']=bootstrap_delta(delta)
        report['results'][str(size)]=rows
        print(size,json.dumps(rows),flush=True)
    (ROOT/'docs/onboarding-evaluation.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':
    with threadpool_limits(limits=1):
        main()
