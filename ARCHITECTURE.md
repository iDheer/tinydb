# TinyDB — Architecture

TinyDB is a small, pure-Python, document-oriented database. A database is a single
Python `dict` of tables (`{table_name: {doc_id: document}}`) that is persisted as a
whole by a pluggable *storage*. All paths below are relative to the repository root.

## 1. Overview of the main components

| # | Component | File | What it does |
|---|-----------|------|--------------|
| 1 | **TinyDB** (database) | `tinydb/database.py` | Entry point. Instantiates the storage from `storage=` (default `JSONStorage`) with all remaining constructor arguments, creates and caches `Table` objects by name, and forwards unknown attributes (`insert`, `search`, …) to the default table `_default`. |
| 2 | **Table / Document** | `tinydb/table.py` | All document operations (insert, search, get, update, upsert, remove, truncate, count). Reads and writes the *whole* database through the storage, owns a per-table LRU **query cache**, and assigns integer document IDs. `Document` is a `dict` with a `doc_id`. |
| 3 | **Query / QueryInstance** | `tinydb/queries.py` | Query builder (`Query().field == 1`, `where('f')`). A query is a callable `doc -> bool` plus a **stable hash value** that describes it; queries combine with `&`, `\|`, `~`. Defines the `QueryLike` protocol that `Table` accepts. |
| 4 | **Storages** | `tinydb/storages.py` | Abstract `Storage` (`read()` / `write(data)` / optional `close()`), plus `JSONStorage` (file on disk) and `MemoryStorage`. Serialisation lives here and only here. |
| 5 | **Middlewares** | `tinydb/middlewares.py` | Wrappers that look like a storage *class* to `TinyDB` and wrap a real storage, e.g. `CachingMiddleware`, which keeps the data in memory and writes it through every `WRITE_CACHE_SIZE` writes, on `flush()` or on `close()`. |
| 6 | **Operations** | `tinydb/operations.py` | Factory functions (`delete`, `add`, `set`, `increment`, …) that return callables mutating a document; passed to `Table.update`. |
| 7 | **Utils** | `tinydb/utils.py` | `LRUCache` (used as the query cache), `freeze`/`FrozenDict` (make query arguments hashable) and `with_typehint` (typing helper so `TinyDB` looks like a `Table` to IDEs). |

`tinydb/mypy_plugin.py` is a type-checking helper only and is not used at runtime.

**Who calls whom**

- `TinyDB.__init__` calls `storage(*args, **kwargs)`. The result can be a storage or a
  middleware chain, and it is passed to every `Table` it creates.
- `Table` calls only `storage.read()` and `storage.write(data)`. It never knows which
  concrete storage or middleware it is talking to.
- `Table.search`/`get`/`update`/`remove` call query objects as plain callables and use
  them as keys in the `LRUCache` query cache. Every write goes through
  `Table._update_table`, which writes the whole data back and then clears the cache.
- `Query` uses `utils.freeze` to build hash values. It does not depend on tables or storages.
- A `Middleware` holds the wrapped storage in `self.storage` and forwards unknown
  attributes to it.

```mermaid
flowchart LR
  User([user code]) --> TinyDB
  TinyDB -- "storage(*args, **kwargs)" --> MW["Middleware (optional)<br/>CachingMiddleware"]
  MW -- wraps --> ST["Storage (ABC)<br/>JSONStorage / MemoryStorage"]
  TinyDB -- "creates / forwards to" --> Table
  Table -- "read() / write(whole dict)" --> MW
  Table -- "read() / write()" -.-> ST
  Table -- "calls cond(doc), uses hash as cache key" --> Query["Query / QueryInstance"]
  Table -- "query cache" --> LRU["utils.LRUCache"]
  Table -- "update(fields=...)" --> Ops["operations"]
  Query -- "freeze() args for hashing" --> Utils["utils.freeze / FrozenDict"]
```

Import layering (lower layers never import upper ones):
`utils` ← `queries`, `storages` ← `table` ← `database`; `middlewares` imports only `Storage`.

## 2. Architecture decision records

### ADR-1: Storages read and write the whole database as one `dict`
**Status:** Verified. The code comment in `tinydb/table.py:808-812` says "The storage
interface used by TinyDB only allows to read/write the complete database data, but not
modifying only portions of it."

- **Context:** TinyDB targets small applications and wants new storage back-ends to be
  trivial to write.
- **Decision:** The storage interface is just `read() -> dict | None` and
  `write(dict)`. `Table._update_table` does read-modify-write on the whole database for
  every change and converts document IDs to `str` before writing, because JSON keys
  must be strings (`tinydb/table.py:842-848`).
- **Alternatives considered:** a per-document/incremental API (insert/update/delete
  methods on the storage), or a real embedded engine such as SQLite.
- **Consequences:** A new storage needs only two methods, and middlewares can wrap any
  storage. On the other hand every write costs O(size of database), `read()` must
  return `None` for an empty store, and storages must handle string document IDs.

### ADR-2: Middlewares wrap storages and pose as the storage class
**Status:** Verified. The design is explained in the `Middleware.__call__` docstring
(`tinydb/middlewares.py:25-63`) and the `__getattr__` forwarding (`tinydb/middlewares.py:67-74`).

- **Context:** Cross-cutting behaviour such as caching should work with every storage
  without changing `TinyDB` or the storages.
- **Decision:** A middleware is constructed with a storage *class*
  (`CachingMiddleware(JSONStorage)`). When `TinyDB` calls it with the user's arguments,
  `__call__` instantiates the real storage and returns the middleware itself, so
  `TinyDB(path, storage=CachingMiddleware(JSONStorage))` works unchanged. Middlewares
  can nest.
- **Alternatives considered:** callbacks/hooks inside `TinyDB` or `Table`, or caching
  subclasses of each storage (`CachedJSONStorage`, …).
- **Consequences:** The storage interface is the only seam between the database and the
  persistence layer. Middleware subclasses must call `super().__init__(storage_cls)`.
  With `CachingMiddleware`, data reaches the wrapped storage only on flush/close, so
  callers must close the database. Storages must accept their configuration through
  constructor arguments, because that is the only channel `TinyDB` forwards.

### ADR-3: Queries carry a stable structural hash used by a per-table query cache
**Status:** Verified. See the `QueryInstance` docstring (`tinydb/queries.py:71-73`), the
`Table` "Query Cache" admonition (`tinydb/table.py:41-50`) and the issue #637 comments
about including regex flags in the hash (`tinydb/queries.py:358-359`).

- **Context:** Searches scan every document. Applications often repeat the same query.
- **Decision:** Every query object has a hash value, a tuple describing what it tests
  (operation tag, field path, frozen arguments). `Table.search` uses the query itself
  as the key into an `LRUCache` (capacity 10). The whole cache is discarded after any
  write. The combinators (`&`, `|`, `~`) build their hash from their operands' hashes
  plus an operator tag (`&` and `|` use a `frozenset` because they are commutative).
  Queries whose result cannot be cached (`map()`, unhashable arguments) set their hash
  to `None`, and `is_cacheable()` then returns `False`.
- **Alternatives considered:** no caching at all, or caching keyed by object identity
  (would rarely hit, since users rebuild queries).
- **Consequences:** Correctness of `search`/`count` depends on two queries with
  different meaning never sharing a hash value. Any new query operation must encode
  *all* of its parameters in its hash. User test functions must be deterministic.

## 3. Constraints (rules not to break)

| # | Constraint | Where it can be seen |
|---|-----------|----------------------|
| C1 | New storages subclass `tinydb.storages.Storage` and implement `read()` and `write()`. `read()` returns `None` for an empty/new store, and `close()` releases resources. | `tinydb/storages.py:36-76` |
| C2 | Every query is built via `Query._generate_test` (which resolves the field path and returns `False` for missing fields) and gets a hash value that includes an operation tag, the path and every argument, or `None` if it must not be cached. | `tinydb/queries.py:218-252` |
| C3 | `Table` changes data only through `_update_table`, which writes the full data back with string document IDs and then clears the query cache. Don't write to storage elsewhere or skip the cache invalidation. | `tinydb/table.py:804-854` |
| C4 | Keep the import layering. `queries.py` imports only `utils`. `storages.py` imports no other TinyDB module. Neither imports `table.py` or `database.py`. | `tinydb/queries.py:23`, `tinydb/storages.py:6-11` |
| C5 | TinyDB has no third-party runtime dependencies. Use only the standard library in `tinydb/` (the `[project]` table declares no `dependencies`). | `pyproject.toml:1-34` |
