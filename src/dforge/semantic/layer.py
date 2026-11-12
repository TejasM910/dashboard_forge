"""Semantic Layer YAML loader, validator, and compiler (T-301 & FR-40)."""

from pathlib import Path
from typing import Dict, List, Optional, Union
import yaml
from dforge.core.models import MetricDefinition


class SemanticLayer:
    """Manages declarative, version-controlled YAML metric definitions (single source of truth)."""

    def __init__(self, metrics: Optional[Dict[str, MetricDefinition]] = None):
        self.metrics: Dict[str, MetricDefinition] = metrics or {}

    def register_metric(self, metric: MetricDefinition) -> None:
        self.metrics[metric.name] = metric

    def get_metric(self, name: str) -> MetricDefinition:
        if name not in self.metrics:
            raise KeyError(f"Metric '{name}' not found in semantic layer.")
        return self.metrics[name]

    def to_yaml(self) -> str:
        """Export all registered metrics to declarative YAML."""
        data = {
            "version": "1.0",
            "metrics": [m.model_dump() for m in self.metrics.values()],
        }
        return yaml.dump(data, sort_keys=False)

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "SemanticLayer":
        """Load and validate metrics from YAML."""
        data = yaml.safe_load(yaml_content) or {}
        metrics_list = data.get("metrics", [])
        layer = cls()
        for m_data in metrics_list:
            metric = MetricDefinition.model_validate(m_data)
            layer.register_metric(metric)
        return layer

    def save_to_file(self, file_path: Union[str, Path]) -> None:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_yaml(), encoding="utf-8")

    @classmethod
    def load_from_file(cls, file_path: Union[str, Path]) -> "SemanticLayer":
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Semantic layer file not found: {path}")
        return cls.from_yaml(path.read_text(encoding="utf-8"))
