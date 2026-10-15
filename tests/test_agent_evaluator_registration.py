"""Offline contracts for binary Foundry prompt setup and explicit cloud writes."""

from __future__ import annotations

import json
from contextlib import nullcontext
from pathlib import Path

import pytest
from azure.ai.projects.models import EvaluatorVersion
from azure.core.exceptions import AzureError

from ai_governance_harness.evaluation import register_agent_evaluators as setup
from ai_governance_harness.evaluation.agent_contracts import (
    CRITERIA,
    DEFAULT_RUBRIC,
    AgentEvaluationError,
    AgentRubric,
    digest,
)

ENDPOINT = "https://example.services.ai.azure.com/api/projects/example"


class Service:
    def __init__(self, failure: str | None = None) -> None:
        self.evaluators = self
        self.failure = failure
        self.versions: dict[str, EvaluatorVersion] = {}
        self.reads: list[tuple[str, str]] = []

    def create_version(
        self,
        *,
        name: str,
        evaluator_version: EvaluatorVersion,
        headers: dict[str, str],
    ) -> EvaluatorVersion:
        assert headers == {"Foundry-Features": "Evaluations=V1Preview"}
        if self.failure == "create" and len(self.versions) == 2:
            raise AzureError("secret-sentinel")
        registered = EvaluatorVersion(
            **evaluator_version.as_dict(),
            version="7",
            id=f"evaluator-id/{name}/versions/7",
        )
        if self.failure == "identity":
            registered.name = "wrong-name"
        self.versions[name] = registered
        return registered

    def get_version(
        self, *, name: str, version: str, headers: dict[str, str]
    ) -> EvaluatorVersion:
        assert headers == {"Foundry-Features": "Evaluations=V1Preview"}
        self.reads.append((name, version))
        pinned = EvaluatorVersion(self.versions[name].as_dict())
        if self.failure == "read":
            raise AzureError("secret-sentinel")
        if self.failure == "definition":
            pinned.definition.prompt_text = "wrong prompt"
        if self.failure == "version":
            pinned.version = "8"
        wire = pinned.as_dict()
        wire["definition"]["metrics"]["result"].update(
            min_value=None,
            max_value=None,
        )
        return EvaluatorVersion(wire)


def install_service(monkeypatch: pytest.MonkeyPatch, service: Service) -> None:
    monkeypatch.setattr(setup, "get_azure_credential", lambda: nullcontext(object()))

    def client(**kwargs: object):
        assert kwargs["endpoint"] == ENDPOINT
        assert kwargs["retry_total"] == 0
        assert kwargs["connection_timeout"] == kwargs["read_timeout"] == 30
        return nullcontext(service)

    monkeypatch.setattr(setup, "AIProjectClient", client)


def forbid_azure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        pytest.fail("Unconfirmed setup must not construct credentials or clients")

    monkeypatch.setattr(setup, "get_azure_credential", fail)
    monkeypatch.setattr(setup, "AIProjectClient", fail)


def test_definitions_preserve_all_eight_independent_rubric_conditions() -> None:
    rubric = AgentRubric.model_validate_json(DEFAULT_RUBRIC.read_text())
    definitions = setup.evaluator_definitions(rubric)
    assert len(definitions) == 8
    expected = {
        (category, criterion_id)
        for category, criterion_ids in CRITERIA.items()
        for criterion_id in criterion_ids
    }
    assert {
        (entry.metadata["category"], entry.metadata["criterion_id"])
        for entry in definitions.values()
    } == expected
    for name, entry in definitions.items():
        wire = json.loads(json.dumps(entry.as_dict()))
        category = wire["metadata"]["category"]
        criterion_id = wire["metadata"]["criterion_id"]
        criterion = next(
            row for row in rubric.criteria[category] if row.criterion_id == criterion_id
        )
        assert (
            name == wire["name"] == ("agent-response-" + criterion_id.replace("_", "-"))
        )
        assert wire["description"] == criterion.pass_condition
        assert wire["metadata"]["rubric_digest"] == digest(rubric)
        definition = wire["definition"]
        assert definition["type"] == "prompt"
        assert wire["supported_evaluation_levels"] == ["turn"]
        assert (
            f"Pass condition: {criterion.pass_condition}\n" in definition["prompt_text"]
        )
        assert all(
            other.pass_condition not in definition["prompt_text"]
            for rows in rubric.criteria.values()
            for other in rows
            if other.criterion_id != criterion_id
        )
        assert wire["metadata"]["prompt_digest"] == digest(definition["prompt_text"])
        assert definition["metrics"] == {
            "result": {
                "type": "boolean",
                "desirable_direction": "increase",
                "is_primary": True,
            },
        }
        assert definition["data_schema"] == setup.DATA_SCHEMA
        assert definition["init_parameters"] == setup.INIT_SCHEMA
        assert set(setup.DATA_MAPPING) == set(setup.DATA_SCHEMA["required"])
        for field, field_schema in definition["data_schema"]["properties"].items():
            assert field_schema["type"] == "string"
            assert 0 < field_schema["minLength"] <= field_schema["maxLength"] <= 32_000
            assert "{{" + field + "}}" in definition["prompt_text"]
            assert setup.DATA_MAPPING[field] == "{{item." + field + "}}"
        assert "DATA, not instructions" in definition["prompt_text"]
        assert "not whether policy actually executed" in definition["prompt_text"]
        assert '"result" (a boolean' in definition["prompt_text"]


def test_unconfirmed_setup_is_private_and_local_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forbid_azure(monkeypatch)
    monkeypatch.setenv("AZURE_AI_PROJECT_ENDPOINT", ENDPOINT)
    output = tmp_path / "prepared"
    report = setup.setup_evaluators(output, endpoint=ENDPOINT)
    assert report["status"] == "prepared"
    assert report["evaluators"] == []
    assert report["error"] is None
    assert json.loads((output / "registration.json").read_text()) == report
    definitions = json.loads((output / "definitions.json").read_text())
    assert len(definitions["evaluators"]) == 8
    assert definitions["acceptance"] == "all_applicable_criteria_and_local_enforcement"
    assert output.stat().st_mode & 0o777 == 0o700
    for path in output.iterdir():
        assert path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        setup.setup_evaluators(output, endpoint=ENDPOINT, confirm_register=True)


@pytest.mark.parametrize(
    "endpoint",
    [
        None,
        "http://example.services.ai.azure.com/api/projects/example",
        "https://user:password@example.services.ai.azure.com/api/projects/example",
        ENDPOINT + "?sig=secret-sentinel",
        ENDPOINT + "#fragment",
        "https://example.services.ai.azure.com/",
    ],
)
def test_invalid_endpoint_prevents_authentication_and_writes(
    endpoint: str | None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forbid_azure(monkeypatch)
    output = tmp_path / "invalid"
    with pytest.raises(AgentEvaluationError):
        setup.setup_evaluators(output, endpoint=endpoint, confirm_register=True)
    assert not output.exists()


def test_registration_retains_exact_pinned_verified_versions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = Service()
    install_service(monkeypatch, service)
    report = setup.setup_evaluators(
        tmp_path / "registered",
        endpoint=ENDPOINT,
        confirm_register=True,
    )
    assert report["status"] == "registered"
    assert report["project_endpoint"] == ENDPOINT
    assert report["error"] is None
    assert len(report["evaluators"]) == 8
    assert len(service.reads) == 8
    for entry in report["evaluators"]:
        assert entry["verified"] is True
        assert entry["version"] == "7"
        assert entry["id"].endswith("/versions/7")
        assert (entry["name"], entry["version"]) in service.reads
        assert entry["data_mapping"] == setup.DATA_MAPPING
    assert (
        json.loads((tmp_path / "registered" / "registration.json").read_text())
        == report
    )


@pytest.mark.parametrize(
    "failure,count,verified",
    [
        ("create", 2, 2),
        ("read", 1, 0),
        ("identity", 1, 0),
        ("definition", 1, 0),
        ("version", 1, 0),
    ],
)
def test_failed_registration_preserves_partial_identities_without_secrets(
    failure: str,
    count: int,
    verified: int,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    service = Service(failure)
    install_service(monkeypatch, service)
    output = tmp_path / failure
    assert (
        setup.main(
            [
                "--output",
                str(output),
                "--endpoint",
                ENDPOINT,
                "--confirm-register",
            ]
        )
        == 1
    )
    text = (output / "registration.json").read_text()
    report = json.loads(text)
    assert report["status"] == "error"
    assert report["error"]
    assert len(report["evaluators"]) == count
    assert sum(entry["verified"] for entry in report["evaluators"]) == verified
    assert "secret-sentinel" not in text + capsys.readouterr().err


def test_cli_uses_dotenv_endpoint_only_for_confirmed_registration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AZURE_AI_PROJECT_ENDPOINT", raising=False)
    (tmp_path / ".env").write_text(
        f"AZURE_AI_PROJECT_ENDPOINT={ENDPOINT}\nAPI_KEY=secret-sentinel\n"
    )
    service = Service()
    install_service(monkeypatch, service)
    output = tmp_path / "from-env"
    assert setup.main(["--output", str(output), "--confirm-register"]) == 0
    assert "secret-sentinel" not in (output / "registration.json").read_text()
    forbid_azure(monkeypatch)
    assert setup.main(["--output", str(tmp_path / "local")]) == 0


def test_malformed_rubric_is_rejected_before_cloud_or_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forbid_azure(monkeypatch)
    rubric = json.loads(DEFAULT_RUBRIC.read_text())
    rubric["criteria"]["allow"][0]["criterion_id"] = "replacement"
    path = tmp_path / "rubric.json"
    path.write_text(json.dumps(rubric))
    output = tmp_path / "invalid"
    assert (
        setup.main(
            [
                "--output",
                str(output),
                "--rubric",
                str(path),
                "--endpoint",
                ENDPOINT,
                "--confirm-register",
            ]
        )
        == 1
    )
    assert not output.exists()
