# 02-2 · Pydantic v2 deep dive

> **Level:** Beginner · **Prerequisites:** [02-1 · First app, routing & params](01_first_app_routing_params.md)
> **Time:** ~45 min · **Verified:** 2026-08-07 (Pydantic 2.11)

## Why this matters

Pydantic is FastAPI's engine room: every request body, response, and (soon) settings object flows through it. Modeling data *well* — tight constraints, explicit rejection of junk, controlled serialization — is what keeps garbage out of your business logic and secrets out of your responses. And because Pydantic **v2** renamed half its API, the internet is full of v1 tutorials that either crash or (worse) silently do nothing on v2 — by the end of this lesson you'll recognize outdated code on sight.

---

## Fields & constraints with `Field()`

Type hints say *what kind*; `Field()` says *how much, how long, what shape*:

```python
from pydantic import BaseModel, Field, HttpUrl

class LinkCreate(BaseModel):
    url: HttpUrl                                   # must parse as a real http(s) URL
    slug: str | None = Field(
        default=None,
        min_length=3,
        max_length=30,
        pattern=r"^[a-z0-9-]+$",                   # regex constraint
    )
    max_clicks: int = Field(default=100, ge=1, le=10_000)   # 1 ≤ x ≤ 10 000
```

- **`HttpUrl`** — one of many rich types (`EmailStr`, `SecretStr`, …) that validate structure, not just "is a string".
- **`ge`/`le`/`gt`/`lt`** for numbers, **`min_length`/`max_length`/`pattern`** for strings.
- Constraints live *on the model*, so every entry point that uses the model — endpoint, test, script — enforces the same rules. Validation logic scattered through function bodies always drifts; declared constraints can't.

---

## Nested models: real request bodies aren't flat

Production payloads have structure — a model's fields can *be* models, and validation recurses through the whole tree:

```python
class Owner(BaseModel):
    name: str = Field(min_length=1)
    email: str

class Tag(BaseModel):
    label: str = Field(max_length=20)

class LinkIn(BaseModel):
    url: HttpUrl
    owner: Owner                    # nested object — validated recursively
    tags: list[Tag] = []            # list of models — each element validated
    meta: dict[str, str] = {}       # free-form key/value pairs
```

A request body like `{"url": ..., "owner": {"name": "", ...}}` fails with a precise error location: `owner → name` — FastAPI reports the *path* into the nested structure, which is what makes deep payloads debuggable from the 422 alone. Three habits:

- **Compose, don't flatten.** `owner_name`, `owner_email` fields are a smell; a nested `Owner` model is reusable across endpoints and keeps constraints in one place.
- **Nested models appear in `/docs` as their own schemas** — clients generate types from them; naming them well is API design.
- **Depth is free for validation but not for reading** — if a model nests more than ~3 levels, that's usually a sign the endpoint is accepting too much in one request.

---

## `ConfigDict`: model-wide behavior

Model-wide options go in `model_config = ConfigDict(...)` — **never** the v1 `class Config:` inner class:

```python
from pydantic import BaseModel, ConfigDict

class LinkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")   # unknown keys → 422
    url: str
    slug: str | None = None

class LinkFromDb(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # read obj.attr, not obj["key"]
    slug: str
    clicks: int
```

The two you'll use constantly:

- **`extra="forbid"`** — reject payloads with unknown keys. The default (`"ignore"`) silently drops them, which hides client typos: a client sending `"slgu"` gets no error and no effect. On input models at a trust boundary, forbid.
- **`from_attributes=True`** — lets `Model.model_validate(orm_obj)` read *attributes* instead of dict keys. This is how ORM objects become API schemas later in the course.

---

## Custom validation: `@field_validator` & `@model_validator`

When constraints aren't enough, write validators — with the **v2 decorators**:

```python
from pydantic import BaseModel, field_validator, model_validator

RESERVED = {"docs", "links", "admin"}

class LinkCreate(BaseModel):
    url: str
    slug: str | None = None

    @field_validator("slug")                    # v1's @validator is gone
    @classmethod
    def slug_not_reserved(cls, v: str | None) -> str | None:
        if v in RESERVED:
            raise ValueError(f"slug {v!r} is reserved")
        return v                                # always return the (possibly fixed) value

    @model_validator(mode="after")              # runs on the built model → cross-field
    def slug_differs_from_url(self) -> "LinkCreate":
        if self.slug and self.slug in self.url:
            raise ValueError("slug must not appear in the target url")
        return self
```

- **`@field_validator("name")`** — one field, runs after that field's type/constraint checks pass. Raise `ValueError` to reject; return the value to accept (you can also normalize here, e.g. `v.lower()`).
- **`@model_validator(mode="after")`** — receives the fully-built instance as `self`; the place for **cross-field** rules, since all fields exist by then. Must return `self`.
- **`mode="before"`** — runs on the *raw input* before any parsing, as a `@classmethod` receiving the incoming data (often a dict, but don't assume). Use it to reshape weird input into something the model can parse:

```python
    @model_validator(mode="before")
    @classmethod
    def unwrap_envelope(cls, data):
        # accept both {"url": ...} and {"data": {"url": ...}}
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        return data
```

---

## `computed_field`: derived values in output

Some values shouldn't be *stored*, only *derived* — deriving means they can never go stale:

```python
from pydantic import BaseModel, computed_field

class LinkStats(BaseModel):
    slug: str
    clicks: int

    @computed_field                     # include this property in serialization + schema
    @property
    def short_url(self) -> str:
        return f"https://lnk.example/{self.slug}"

LinkStats(slug="abc", clicks=3).model_dump()
# {'slug': 'abc', 'clicks': 3, 'short_url': 'https://lnk.example/abc'}
```

A plain `@property` is invisible to `model_dump()` and to the OpenAPI schema; stacking `@computed_field` on top puts it in both. The return annotation is required — it's what generates the schema type.

---

## Serialization: `model_dump` vs `model_dump_json`

```python
link = LinkStats(slug="abc", clicks=3)

link.model_dump()                        # → Python dict (values stay Python objects)
link.model_dump(mode="json")             # → dict, but JSON-safe values (datetime → str, …)
link.model_dump_json()                   # → JSON *string*, in one efficient pass

link.model_dump(exclude={"clicks"})      # drop fields ad hoc
link.model_dump(include={"slug"})        # or keep only these
```

- **`model_dump()`** when Python code consumes the result; **`model_dump_json()`** when it goes over the wire yourself. (Inside FastAPI endpoints you usually return the model and let the framework serialize.)
- **`exclude`/`include`** are for one-off cases. For "this field must never leave the API", don't rely on remembering `exclude` at every call site — use a response model, next lesson.
- The v1 names `.dict()` / `.json()` are removed. Seeing them = v1 code.

---

## Aliases: Python names in, camelCase out

Your Python is `snake_case`; many frontends want `camelCase`. Don't rename fields — alias them:

```python
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

class LinkStats(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,       # click_count ⇄ clickCount, for every field
        populate_by_name=True,          # accept the Python name on input too
    )
    slug: str
    click_count: int

LinkStats.model_validate({"slug": "abc", "clickCount": 3})   # alias in ✓
LinkStats(slug="abc", click_count=3)                          # Python name in ✓ (populate_by_name)
LinkStats(slug="abc", click_count=3).model_dump(by_alias=True)
# {'slug': 'abc', 'clickCount': 3}
```

`alias_generator` computes every alias from the field name — no per-field `Field(alias=...)` litter. `populate_by_name=True` keeps your own code (and tests) writing normal Python names. `by_alias=True` at dump time chooses the external spelling.

---

## `TypeAdapter`: validation without a model

Sometimes the thing to validate isn't a model — it's a `list[Link]` from a JSON file, or a bare `HttpUrl`. `TypeAdapter` gives any type the validation machinery:

```python
from pydantic import TypeAdapter

links_adapter = TypeAdapter(list[LinkCreate])          # build once, reuse (it compiles a validator)

links = links_adapter.validate_python(raw_list)        # list[dict] → list[LinkCreate], or raise
blob = links_adapter.dump_json(links)                  # and back to JSON bytes

TypeAdapter(HttpUrl).validate_python("not a url")      # ValidationError — no model needed
```

Wrapping the list in a throwaway `class LinkList(BaseModel): items: list[LinkCreate]` just to validate it is the v1-era workaround; `TypeAdapter` replaces it. Build adapters once at module level — construction compiles the validator, so it isn't free in a hot loop.

---

## Recognizing v1 code in the wild

Most FastAPI tutorials older than ~2023 use Pydantic v1. The renames:

| Pydantic v1 (outdated) | Pydantic v2 (use this) |
|---|---|
| `@validator` | `@field_validator` |
| `@root_validator` | `@model_validator` |
| `class Config:` | `model_config = ConfigDict(...)` |
| `.dict()` / `.json()` | `.model_dump()` / `.model_dump_json()` |
| `.parse_obj()` / `.parse_raw()` | `.model_validate()` / `.model_validate_json()` |
| `parse_obj_as(list[X], data)` | `TypeAdapter(list[X]).validate_python(data)` |
| `orm_mode = True` | `from_attributes=True` |

Some v1 spellings raise loud errors on v2; others merely emit deprecation warnings and limp along — and v1 code copy-pasted into a v2 model can **silently never run** (you'll hunt exactly that bug in this section's gate). If a tutorial shows anything from the left column, translate as you read — or find a newer tutorial.

---

## Recap & next

- ✅ `Field()` declares constraints (`min_length`, `ge`, `pattern`) on the model — one source of truth for every entry point.
- ✅ `ConfigDict(extra="forbid")` rejects unknown keys; `from_attributes=True` reads ORM objects. Never `class Config`.
- ✅ `@field_validator` for one field, `@model_validator(mode="after")` for cross-field rules, `mode="before"` to reshape raw input.
- ✅ `@computed_field` puts derived values into dumps *and* the schema; `model_dump` → dict, `model_dump_json` → string.
- ✅ `alias_generator=to_camel` + `populate_by_name=True` for camelCase APIs; `TypeAdapter` validates non-model types.
- ✅ Self-check: why does a cross-field rule belong in `@model_validator(mode="after")` rather than in a `@field_validator`?

→ Next: **[02-3 · Response models, settings & lifespan](03_response_models_settings_lifespan.md)**

## Exercises

1. Add a `tags: list[str]` field to `LinkCreate` (max 5 tags, each 1–20 chars) and a validator that lowercases and de-duplicates them while preserving order.

<details>
<summary>Solution</summary>

```python
class LinkCreate(BaseModel):
    url: str
    tags: list[str] = Field(default_factory=list, max_length=5)

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, v: list[str]) -> list[str]:
        for tag in v:
            if not 1 <= len(tag) <= 20:
                raise ValueError(f"tag {tag!r} must be 1–20 chars")
        return list(dict.fromkeys(t.lower() for t in v))   # dedupe, keep order
```

`max_length=5` on a list constrains item count. `dict.fromkeys` is the stdlib idiom for order-preserving dedupe. Note the mutable-default rule from Section 01: `default_factory=list`, never `default=[]`.
</details>

2. This model (found in a 2021 tutorial) accepts `{"username": "x"}` with no error. Why, and what's the v2 fix?

```python
class User(BaseModel):
    username: str

    @root_validator
    def check(cls, values):
        if len(values["username"]) < 3:
            raise ValueError("too short")
        return values
```

<details>
<summary>Solution</summary>

`@root_validator` is v1. On Pydantic v2 this raises `PydanticUserError` at class definition — unless the import quietly came from `pydantic.v1`, in which case the v2 metaclass never registers it and it **silently never runs**, so `"x"` sails through. The v2 fix:

```python
class User(BaseModel):
    username: str

    @model_validator(mode="after")
    def check(self) -> "User":
        if len(self.username) < 3:
            raise ValueError("too short")
        return self
```

(Here a plain `username: str = Field(min_length=3)` would be even better — reach for declared constraints before custom validators.)
</details>

3. Given `raw = '[{"slug": "a1b", "url": "https://x.dev"}, {"slug": "!!", "url": "nope"}]'` (a JSON string), validate it into `list[LinkCreate]` in one call — no loop, no wrapper model — and report which entry failed.

<details>
<summary>Solution</summary>

```python
from pydantic import TypeAdapter, ValidationError

adapter = TypeAdapter(list[LinkCreate])
try:
    links = adapter.validate_json(raw)      # parses the JSON string directly
except ValidationError as e:
    for err in e.errors():
        print(err["loc"], err["msg"])       # loc starts with the list index, e.g. (1, 'slug')
```

`validate_json` parses and validates in one pass (faster than `json.loads` + `validate_python`). Each error's `loc` begins with the failing index, so you know *which* entry was bad.
</details>
