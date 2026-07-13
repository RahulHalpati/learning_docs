# Changelog

All notable changes to `pokesdk` are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-06-04

### Added
- Synchronous `PokeClient` and asynchronous `AsyncPokeClient`, sharing a common
  `BaseClient` core (config, auth headers, retry policy, backoff).
- `client.pokemon.get(name_or_id)` returning a typed `Pokemon` model.
- `client.pokemon.list_all()` with transparent, lazy pagination (sync + async).
- Exception hierarchy: `PokeError` → `PokeConnectionError` / `APIError`
  (`NotFoundError`, `AuthenticationError`, `RateLimitError`, `ServerError`).
- Automatic retries with exponential backoff on `429`/`5xx`/connection errors.
- Bearer-token auth via the `api_key` argument.
- Full type hints with a shipped `py.typed` marker.

[Unreleased]: https://github.com/you/pokesdk/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/you/pokesdk/releases/tag/v0.1.0
