from backend.ml.ranking import diversify, series_key, is_bundle
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.recommender import Recommender
from test_recommender import book


def titled(id, title, author):
    return {**book(id,['fantasy'],author), 'title': title}


def test_discovery_limits_and_preserves_score_order():
    candidates=[titled(1,'One (Saga, #1)','A'),titled(2,'Two (Saga, #2)','A'),
                titled(3,'Standalone','A'),titled(4,'Third','A'),
                titled(5,'Boxed Set','B'),titled(6,'Other','C'),titled(7,'Another','D')]
    assert [b['id'] for b in diversify(candidates,10)] == [1,3,6,7]
    assert [b['id'] for b in diversify(candidates,2)] == [1,3]
    assert diversify([],10)==[]
    assert series_key(candidates[0])=='saga'
    assert is_bundle(titled(8,'Trilogy (Books, #1-3)','A'))
    assert not is_bundle(titled(9,'The Music Box','A'))


def test_api_discovery_excludes_rated_and_can_be_disabled():
    with TestClient(app) as client:
        app.state.model=Recommender([titled(1,'A','Writer'),titled(2,'B','Writer'),
                                    titled(3,'C','Writer'),titled(4,'D','Other')])
        result=client.post('/api/recommendations',json={'ratings':[],'diverse':True}).json()
        assert result['ranking_policy']=='discovery-v1'
        assert len(result['books'])==3
        result=client.post('/api/recommendations',json={'ratings':[{'book_id':1,'rating':5}],'diverse':True}).json()
        assert 1 not in [b['id'] for b in result['books']]
        assert len(client.post('/api/recommendations',json={}).json()['books'])==4
