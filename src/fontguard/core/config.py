from pathlib import Path

import yaml
from pydantic import Field

from fontguard.core.models import Model, RiskLevel


class UnknownRule(Model):
    action: str = Field(default="unknown", pattern=r"^(unknown|review|high)$")


class Policy(Model):
    fail_on: list[RiskLevel] = Field(default_factory=lambda: [RiskLevel.HIGH])
    allowed_licenses: list[str] = Field(default_factory=list)
    denied_fonts: list[str] = Field(default_factory=list)
    allowed_fonts: list[str] = Field(default_factory=list)
    unknown_font: UnknownRule = Field(default_factory=UnknownRule)


class Config(Model):
    version: int = Field(default=1, ge=1, le=1)
    policy: Policy = Field(default_factory=Policy)


def load_config(path: Path | None) -> Config:
    if path is None:
        return Config()
    return Config.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def failure_levels(values: list[RiskLevel]) -> set[RiskLevel]:
    # UNKNOWN is separate from the ordered known risks.
    order = [RiskLevel.SAFE, RiskLevel.LOW, RiskLevel.REVIEW, RiskLevel.HIGH]
    result: set[RiskLevel] = set()
    for value in values:
        if value == RiskLevel.UNKNOWN:
            result.add(value)
        else:
            result.update(order[order.index(value) :])
    return result
