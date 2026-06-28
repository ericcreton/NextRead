from backend.app.recommender import Recommender

def book(id, genres, author='Someone', count=1000, rating=4):
    return dict(id=id, title=f'Book {id}', authors=author, year='2000', genres=genres, ratings_count=count, average_rating=rating)

def test_positive_and_negative_preferences():
    model = Recommender([book(1,['fantasy']),book(2,['fantasy']),book(3,['romance']),book(4,['romance'])])
    result = model.recommend({1:5,3:1})
    assert [b['id'] for b in result['books']] == [2,4]
    assert 'fantasy' in result['books'][0]['reason']
    assert result['profile'] == [{'genre':'fantasy','strength':100}]

def test_cold_start_shrinks_small_sample_average():
    model = Recommender([book(1,[],count=1,rating=5),book(2,[],count=100000,rating=4.8),book(3,[],count=100000,rating=3)])
    assert model.recommend({})['books'][0]['id'] == 2
    assert model.recommend({})['method'] == 'popularity'

def test_neutral_ratings_excluded_and_fallback():
    model = Recommender([book(1,['fantasy']),book(2,['fantasy'])])
    result = model.recommend({1:3})
    assert result['method'] == 'popularity'
    assert [b['id'] for b in result['books']] == [2]
    assert model.recommend({1:5,2:5})['books'] == []

def test_empty_catalog():
    assert Recommender([]).recommend({})['books'] == []
