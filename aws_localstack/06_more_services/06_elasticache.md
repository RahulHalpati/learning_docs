# 06-6 · ElastiCache: caching

> **Level:** Intermediate · **Prerequisites:** [06-5 RDS](05_rds.md)
> **Time:** 25 min · **Verified:** 2026-09-01 (Floci latest; backed by a real `valkey/valkey:8` engine, confirmed with a live `redis-py` round-trip)

RDS just gave you a real, but comparatively slow, database. **ElastiCache** is
AWS's managed in-memory cache — the thing you put in front of RDS or DynamoDB
so the database only sees the requests that actually need it.

## Real engine, one honest naming note

Like RDS, Floci backs this with a genuine container — but be precise about
which one: `elasticache create-replication-group --engine redis` spins up
`valkey/valkey:8`, not Redis Inc.'s Redis. **Valkey is the open-source fork of
Redis** (created after Redis's 2024 license change) and is wire-compatible —
every Redis client, including `redis-py`, talks to it identically. On real AWS,
"ElastiCache for Redis" has quietly meant Valkey under the hood for new
clusters too, so this isn't even a Floci simplification.

```bash
awslocal elasticache create-replication-group \
  --replication-group-id linkstash-cache --replication-group-description "linkstash" \
  --engine redis --cache-node-type cache.t3.micro --num-cache-clusters 1
```

(Note the API call: `create-cache-cluster` only accepts `memcached` on modern
AWS — Redis/Valkey clusters go through `create-replication-group`, even for a
single node. Floci enforces this exact real-AWS constraint; it's not
arbitrary.)

```bash
awslocal elasticache describe-replication-groups --replication-group-id linkstash-cache \
  --query 'ReplicationGroups[0].[Status,NodeGroups[0].PrimaryEndpoint.Address,NodeGroups[0].PrimaryEndpoint.Port]' --output text
```

Verified output: `available   localhost   6379`, backed by container
`floci-valkey-linkstash-cache` running image `valkey/valkey:8`.

## Use it — the cache-aside pattern

The pattern that matters, not just "connect and SET/GET": **check the cache
first, fall through to the real store on a miss, then populate the cache** for
next time.

```python
import redis
cache = redis.Redis(host="localhost", port=6379, decode_responses=True)

def get_url(slug: str) -> str | None:
    cached = cache.get(f"slug:{slug}")
    if cached is not None:
        return cached                                # cache hit — no DynamoDB call

    item = table.get_item(Key={"slug": slug}).get("Item")   # cache miss — go to the source of truth
    if item:
        cache.set(f"slug:{slug}", item["url"], ex=300)       # populate, 5-minute TTL
    return item["url"] if item else None
```

Verified: `cache.set("slug:abc123", "https://example.com"); cache.get("slug:abc123")`
round-tripped for real against the container above.

This is exactly the read path a link-shortener redirect needs — the hot path
(`GET /:slug`) hits DynamoDB *once* per slug per 5 minutes instead of on every
single click.

## The part that actually causes outages: invalidation

"There are only two hard things in computer science: cache invalidation and
naming things." The bug that bites in production isn't caching — it's a
**stale cache**: someone updates the URL for `abc123` and the cache keeps
serving the old value for up to 5 minutes.

```python
def update_url(slug: str, new_url: str):
    table.update_item(Key={"slug": slug}, UpdateExpression="SET url = :u",
                       ExpressionAttributeValues={":u": new_url})
    cache.delete(f"slug:{slug}")     # ← invalidate on write, don't wait for TTL
```

Rule of thumb: **write-through invalidation** (delete/update the cache key the
moment the source of truth changes) beats relying on a short TTL alone — TTL is
your safety net for the invalidation you forgot, not your primary strategy.

## Where a cache actually earns its cost

Caching isn't free — it's another thing that can be wrong, another point of
failure, another thing to invalidate correctly. Reach for it when:

- The same read happens **often** relative to writes (a popular slug, a hot
  product page) — caching a rarely-read key wastes memory for nothing.
- The underlying read is **expensive** (a join, an aggregate, a cross-service
  call) — caching a single `get_item` saves less than caching a report that
  takes 2 seconds to compute.
- **Staleness for a few minutes is acceptable** — if every read must reflect
  the absolute latest write, you need invalidation discipline (above), not
  just a TTL and hope.

## Access & IAM

`elasticache:*` actions are IAM-gated like any service; the *data itself*
(what's actually cached) usually needs its own auth if the cluster is exposed —
**Redis AUTH**/an ElastiCache auth token, separate from IAM, since the cache
protocol isn't natively IAM-aware the way the AWS API is. Don't rely on network
isolation (a private subnet) alone if the cache ever holds anything sensitive.

## Recap & next

- ✅ ElastiCache = managed in-memory cache; Floci backs Redis/Valkey mode with a
  **real Valkey engine** (the modern open-source Redis fork — genuinely how AWS
  runs it too), verified with a live round-trip.
- ✅ The pattern that matters is **cache-aside**: check cache → miss → read
  source of truth → populate cache.
- ✅ **Invalidate on write**, don't rely on TTL alone — that's where cache bugs
  actually come from in production.
- ✅ Cache when reads are frequent + expensive + some staleness is tolerable;
  otherwise it's cost and complexity with no payoff.

## Exercise

Two requests for the same never-before-seen slug arrive at the exact same
instant, both miss the cache, and both query DynamoDB and then both write to
the cache. Is this a bug? What's the actual failure mode to worry about here,
and is it worse than the naive code above suggests?

<details>
<summary>Answer</summary>

Not a correctness bug — both requests write the *same* correct value to the
cache, so the end state is fine; you just did one redundant DynamoDB read
("cache stampede" on a single key, harmless at this scale). The real risk
version is a **popular** key expiring under heavy concurrent load: hundreds of
requests all miss at once and all hammer DynamoDB simultaneously. The fix is
locking/single-flight (only one request repopulates, others wait) or staggering
TTLs so hot keys don't all expire at the same instant — worth knowing the name
("cache stampede") even if you don't implement the fix here.

</details>

**→ Next: [06-7 · The pattern scales: every other service](07_every_other_service.md)**
