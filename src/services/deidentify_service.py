"""Core services for de-identification strategies."""

from __future__ import annotations

import random
import re
from typing import Any, Dict, List, Tuple

from app.config import POLICY_VERSION
from src.schemas import DeidRequest, DeidResponse


class DeidStrategy:
    """Strategy interface for de-identifying a batch of texts."""

    def deidentify_texts(
        self, texts: List[str], options: Dict[str, Any]
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """根据给定策略对文本列表执行去标识化。"""

        raise NotImplementedError


STRATEGY_REGISTRY: Dict[str, DeidStrategy] = {}


def register_strategy(name: str):
    """Decorator to register a de-identification strategy."""

    def deco(cls: type[DeidStrategy]) -> type[DeidStrategy]:
        STRATEGY_REGISTRY[name] = cls()
        return cls

    return deco


@register_strategy("default")
class RandomDigitReplacement(DeidStrategy):
    """Replace digits with random digits while keeping deterministic seeds."""

    digit_re = re.compile(r"\d+")

    def deidentify_texts(
        self, texts: List[str], options: Dict[str, Any]
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """按输入顺序替换文本中的数字并返回映射。"""

        seed = options.get("seed")
        rng = random.Random(seed)
        mapping: Dict[str, str] = {}

        def _replace(match: re.Match[str]) -> str:
            original = match.group(0)
            if original in mapping:
                return mapping[original]
            replacement = "".join(str(rng.randint(0, 9)) for _ in original)
            mapping[original] = replacement
            return replacement

        deidentified_texts: List[str] = []
        for text in texts:
            deidentified_texts.append(self.digit_re.sub(_replace, text))

        mapping_list = [
            {"type": "NUMBER", "original": original, "pseudo": pseudo}
            for original, pseudo in mapping.items()
        ]
        return deidentified_texts, mapping_list


def build_deid_response(req: DeidRequest) -> DeidResponse:
    """Apply the configured de-identification strategy and build a response."""

    policy_id = req.policy_id or "default"
    strategy = STRATEGY_REGISTRY.get(policy_id)
    if strategy is None:
        raise KeyError(policy_id)
    options = req.options.model_dump() if req.options else {}
    deid_texts, mapping_list = strategy.deidentify_texts(req.text, options)
    mapping: List[Dict[str, str]] | None = (
        mapping_list if options.get("return_mapping") else None
    )
    return DeidResponse(
        deidentified=deid_texts,
        mapping=mapping,
        policy_version=POLICY_VERSION,
    )
