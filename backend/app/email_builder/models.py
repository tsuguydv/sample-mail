from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


Context = dict[str, Any]


@dataclass(slots=True)
class EmailBlock:
    name: str
    context: Context = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BlockMetadata:
    name: str
    description: str
    parameters: dict[str, str]
    example: Context
