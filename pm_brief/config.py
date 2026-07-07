import json
from pathlib import Path
from typing import Any, Dict, List

from pm_brief.models import Source


def load_config(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_sources(config: Dict[str, Any]) -> List[Source]:
    return [
        Source(
            name=item["name"],
            url=item["url"],
            category=item["category"],
            quality=int(item.get("quality", 3)),
            language=item.get("language", "en"),
            tier=int(item.get("tier", 2)),
            failure_policy=item.get("failure_policy", "skip_when_unstable"),
        )
        for item in config.get("sources", [])
        if item.get("enabled", True)
    ]


def load_manual_sources(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(config.get("manual_sources", []))


def resolve_config_path(config_path: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    base_dir = config_path.parent.parent if config_path.parent.name == "config" else config_path.parent
    return base_dir / path
