from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.recommender import Recommender
from test_recommender import book

def test_api_contract():
    with TestClient(app) as client:
        app.state.model = Recommender([book(1,['fantasy']),book(2,['romance'])])
        assert client.get('/api/books?q=BOOK%201').json()['total'] == 1
        assert client.get('/api/books?limit=0').status_code == 422
        assert client.post('/api/recommendations',json={'ratings':[{'book_id':1,'rating':5}]}).json()['books'][0]['id'] == 2
        for ratings in [[{'book_id':9,'rating':5}],[{'book_id':1,'rating':6}],[{'book_id':1,'rating':2.5}],[{'book_id':1,'rating':5}]*2]:
            assert client.post('/api/recommendations',json={'ratings':ratings}).status_code == 422
