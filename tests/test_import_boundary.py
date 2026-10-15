"""Keep preview toolkit imports inside the versioned governance adapter."""

import ast
from pathlib import Path


def test_given_source_imports_when_scanning_then_toolkit_boundary_holds() -> None:
    source = Path(__file__).resolve().parents[1] / "src"
    forbidden = (
        "agentmesh.identity",
        "agent_os.integrations.citadel",
        "agentmesh.integrations.mcp",
    )
    toolkit = {"agentmesh", "agent_os", "agent_sre", "agent_sandbox"}
    for path in source.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            modules = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
                modules.extend(f"{node.module}.{alias.name}" for alias in node.names)
            for module in modules:
                assert not any(
                    module == name or module.startswith(name + ".")
                    for name in forbidden
                ), path
                if module.split(".")[0] in toolkit:
                    assert "governance" in path.relative_to(source).parts, path
