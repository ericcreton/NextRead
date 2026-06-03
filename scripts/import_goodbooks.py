"""Download the source catalog and genre tags, then transactionally upsert books."""
import csv
import ssl
import certifi
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.db import Base, Book, ROOT, Session, engine

SOURCE = 'https://raw.githubusercontent.com/zygmuntz/goodbooks-10k/master/'
GENRES = {'fantasy', 'science-fiction', 'classics', 'romance', 'mystery', 'thriller', 'horror', 'historical-fiction', 'young-adult', 'non-fiction', 'biography', 'memoir', 'poetry', 'adventure', 'dystopia', 'history', 'humor', 'children'}

def rows(name):
    path = ROOT / 'data' / name
    if not path.exists():
        print(f'Downloading {name}...', flush=True)
        temporary = path.with_suffix('.tmp')
        with urllib.request.urlopen(SOURCE + name, timeout=120, context=ssl.create_default_context(cafile=certifi.where())) as response, temporary.open('wb') as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        temporary.replace(path)
    with path.open(encoding='utf-8', newline='') as source:
        yield from csv.DictReader(source)

def main():
    tags = {int(r['tag_id']): r['tag_name'] for r in rows('tags.csv') if r['tag_name'] in GENRES}
    genres = defaultdict(list)
    for row in rows('book_tags.csv'):
        tag = tags.get(int(row['tag_id']))
        if tag and int(row['count']) > 0:
            genres[int(row['goodreads_book_id'])].append((int(row['count']), tag))
    Base.metadata.create_all(engine)
    count = 0
    with Session.begin() as session:
        for row in rows('books.csv'):
            session.merge(Book(id=int(row['book_id']), title=row['title'], authors=row['authors'],
                year=row['original_publication_year'].removesuffix('.0'), average_rating=float(row['average_rating']),
                ratings_count=int(row['ratings_count']), genres=[g for _, g in sorted(genres[int(row['goodreads_book_id'])], reverse=True)[:5]]))
            count += 1
    print(f'Imported {count:,} books. Restart the API to load the catalog.')

if __name__ == '__main__':
    main()
