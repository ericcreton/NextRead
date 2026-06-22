"""Deterministic discovery policy, shared by API and benchmarks."""
import re
from collections import Counter


def author_key(book):
    return book['authors'].split(',')[0].strip().casefold() or f"unknown:{book['id']}"


def series_key(book):
    match = re.search(r'\(([^()]+),\s*#\d', book['title'])
    return match.group(1).strip().casefold() if match else None


def is_bundle(book):
    return bool(re.search(r'\b(box(?:ed)?\s*set|omnibus|\d+[- ]book\s+(?:collection|set))\b|#\d+\s*[-–]\s*\d+', book['title'], re.I))


def diversify(ranked_books, limit):
    """At most two primary-author books and one parsed series; skip known bundles.

    Constraints stay strict: a small candidate catalog can return fewer results.
    This does not infer reading order or detect every bundle/series.
    """
    authors, series = Counter(), set()
    selected = []
    for book in ranked_books:
        author, saga = author_key(book), series_key(book)
        if is_bundle(book) or authors[author] >= 2 or (saga and saga in series):
            continue
        selected.append(book)
        authors[author] += 1
        if saga:
            series.add(saga)
        if len(selected) >= limit:
            break
    return selected
