"""Pydantic models for the PokéAPI resources this SDK exposes.

These are deliberately small subsets of the real PokéAPI payloads — an SDK
should model the fields it promises to support, not blindly mirror every field
the server happens to return. Unknown fields are ignored (the default), so the
SDK keeps working when the API adds new ones.
"""

from __future__ import annotations

from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class NamedResource(BaseModel):
    """A {name, url} reference, the PokéAPI's way of linking to another resource."""

    name: str
    url: str


class PokemonType(BaseModel):
    slot: int
    type: NamedResource


class PokemonStat(BaseModel):
    base_stat: int
    stat: NamedResource


class Pokemon(BaseModel):
    """A single Pokémon, e.g. the result of ``client.pokemon.get("ditto")``."""

    model_config = ConfigDict(frozen=True)  # immutable: response objects shouldn't be mutated

    id: int
    name: str
    height: int
    weight: int
    base_experience: Optional[int] = None
    types: List[PokemonType] = []
    stats: List[PokemonStat] = []


class Page(BaseModel, Generic[T]):
    """One page of a list endpoint: results plus links to neighbouring pages."""

    count: int
    next: Optional[str] = None
    previous: Optional[str] = None
    results: List[T] = []
