from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .models import OperationDefinition, PARAMETER_MODELS, StrictModel


class CatalogDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    catalog_version: str = Field(min_length=1)
    operations: list[OperationDefinition]


class OperationCatalog:
    def __init__(self, document: CatalogDocument):
        self.version = document.catalog_version
        self._operations = {item.operation_id: item for item in document.operations}
        if len(self._operations) != len(document.operations):
            raise ValueError("duplicate operation_id in catalog")
        for item in document.operations:
            if item.parameter_schema not in PARAMETER_MODELS:
                raise ValueError(f"unknown parameter schema: {item.parameter_schema}")

    @classmethod
    def load(cls, path: Path) -> "OperationCatalog":
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls(CatalogDocument.model_validate(raw))

    def list(self) -> list[OperationDefinition]:
        return sorted(self._operations.values(), key=lambda item: item.operation_id)

    def get(self, operation_id: str) -> OperationDefinition | None:
        return self._operations.get(operation_id)

    def validate_parameters(self, definition: OperationDefinition, parameters: dict) -> StrictModel:
        model_type = PARAMETER_MODELS[definition.parameter_schema]
        return model_type.model_validate(parameters)
