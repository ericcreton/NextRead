import numpy as np
from scipy import sparse
from backend.ml.data import split_ratings
from backend.ml.model import FactorModel, ranking_metrics, top_k
from backend.app.hybrid import HybridRecommender
from test_recommender import book


def toy():
    return FactorModel(np.array([10,20,30,40]), np.array([[1.,0.],[.9,.1],[0.,1.],[.1,.9]]),
                       np.array([4.,3.,2.,1.]), sparse.eye(4,format='csr'), .75)


def test_split_reproducible_and_disjoint():
    data = np.array([[u,b,4] for u in [1,2] for b in range(1,21)] + [[3,1,5]])
    labels = split_ratings(data)
    assert np.array_equal(labels,split_ratings(data))
    assert np.bincount(labels).tolist() == [33,4,4]
    assert labels[-1] == 0
    for u in [1,2]:
        assert np.bincount(labels[data[:,0]==u]).tolist() == [16,2,2]


def test_metrics_known_example():
    result = ranking_metrics([1,2,3],{1,3},k=3)
    np.testing.assert_allclose(result,[2/3,1,1.5/(1+1/np.log2(3))])
    assert ranking_metrics([1,2],set(),k=2).tolist() == [0,0,0]


def test_fold_in_exclusion_and_negative_feedback():
    model=toy()
    positive = model.components({10:5})[0]
    negative = model.components({10:1})[0]
    assert positive[1]>positive[2]
    assert negative[1]<negative[2]
    assert 0 not in top_k(positive,[0],10)
    assert top_k(np.ones(4),[],2).tolist() == [0,1]
    np.testing.assert_equal(model.scores({10:3}),model.popularity)


def test_artifact_roundtrip_and_online_equivalence(tmp_path):
    model=toy()
    path=tmp_path/'run'
    model.save(path,{'test':True})
    loaded=FactorModel.load(path)
    np.testing.assert_allclose(model.scores({10:5}),loaded.scores({10:5}))
    books=[book(i,['fantasy']) for i in [10,20,30,40]]
    wrapper=HybridRecommender(books,loaded,'test')
    result=wrapper.recommend({10:5},2)
    indices=top_k(loaded.scores({10:5}),[0],2)
    assert [b['id'] for b in result['books']] == loaded.ids[indices].tolist()
    assert result['method']=='hybrid-svd'
    assert wrapper.recommend({})['method']=='popularity'
