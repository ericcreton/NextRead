# Dataset attribution

NextRead uses **Goodbooks-10k**, published by **Zygmunt Zając**:

- Original source: https://github.com/zygmuntz/goodbooks-10k
- Original license notice: https://github.com/zygmuntz/goodbooks-10k/blob/master/LICENSE
- License: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0), https://creativecommons.org/licenses/by-sa/4.0/

Goodbooks contains historical Goodreads book metadata, user ratings and tags. The dataset publisher and Goodreads do not endorse NextRead.

## Transformations

NextRead downloads books.csv, tags.csv and book_tags.csv, joins tags by goodreads_book_id, filters to an explicit genre allowlist, and retains up to five genres per book. It loads ratings.csv, partitions interactions reproducibly, derives content features and learns matrix factors. The source is not modified in place. Reports describe these transformations and include dataset checksums.

Raw CSVs, the SQL database, split arrays and model artifacts remain local under data/ and are excluded from Git. The repository distributes application code, regeneration scripts and aggregate experiment reports. If you redistribute original or adapted dataset material, preserve its attribution and comply with its CC BY-SA terms. Dataset licensing is separate from any application-code license; this notice does not relicense upstream materials.
