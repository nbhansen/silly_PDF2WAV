"""Regression test: application services must not import from infrastructure."""

import ast
from pathlib import Path

import pytest


@pytest.mark.unit
class TestLayerBoundaries:
    """Ensure hexagonal architecture boundaries are respected."""

    def test_document_service_has_no_infrastructure_imports(self) -> None:
        """DocumentProcessingService must not import from infrastructure/."""
        source = Path("application/services/document_service.py").read_text()
        tree = ast.parse(source)

        violations: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("infrastructure"):
                violations.append(f"line {node.lineno}: from {node.module} import ...")

        assert violations == [], f"Infrastructure imports found in document_service.py:\n" + "\n".join(violations)

    def test_document_service_does_not_construct_domain_objects(self) -> None:
        """DocumentProcessingService must not directly construct TextPipeline."""
        source = Path("application/services/document_service.py").read_text()
        assert "TextPipeline(" not in source, "Direct TextPipeline construction found — use container instead"
