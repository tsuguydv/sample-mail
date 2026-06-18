from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from .models import Context, EmailBlock
from .registry import DESIGN_DEFAULTS, get_block_metadata


class EmailBuilder:
    def __init__(
        self,
        *,
        templates_dir: str | Path | None = None,
        layout_template: str = "layout/base.html",
        design: Context | None = None,
    ) -> None:
        root = Path(__file__).resolve().parents[2]
        self.templates_dir = Path(templates_dir) if templates_dir else root / "templates" / "modular"
        self.layout_template = layout_template
        self.design = {**DESIGN_DEFAULTS, **(design or {})}
        self.blocks: list[EmailBlock] = []
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(enabled_extensions=("html", "xml"), default_for_string=True),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def add_block(self, name: str, context: Context | None = None) -> "EmailBuilder":
        get_block_metadata(name)
        metadata = get_block_metadata(name)
        merged_context = {**deepcopy(metadata.example), **(context or {})}
        self.blocks.append(EmailBlock(name=name, context=merged_context))
        return self

    def remove_block(self, identifier: int | str) -> EmailBlock:
        if isinstance(identifier, int):
            try:
                return self.blocks.pop(identifier)
            except IndexError as exc:
                raise IndexError(f"Block index {identifier} is out of range") from exc

        for index, block in enumerate(self.blocks):
            if block.name == identifier:
                return self.blocks.pop(index)
        raise ValueError(f"Block '{identifier}' was not added")

    def clear(self) -> None:
        self.blocks.clear()

    def render(self, extra_context: Context | None = None) -> str:
        rendered_blocks = [self._render_block(block) for block in self.blocks]
        template = self.env.get_template(self.layout_template)
        context: dict[str, Any] = {
            **self.design,
            **(extra_context or {}),
            "blocks": rendered_blocks,
        }
        return template.render(**context)

    def _render_block(self, block: EmailBlock) -> str:
        template = self.env.get_template(f"blocks/{block.name}.html")
        return template.render(**self.design, **block.context)
