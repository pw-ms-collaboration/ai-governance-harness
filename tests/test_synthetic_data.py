"""Unit tests for synthetic superannuation data schemas and generation."""

import json
from pathlib import Path

from ai_governance_harness.synthetic_data.schemas import (
    MemberRecord,
)
from ai_governance_harness.synthetic_data.generator import (
    build_synthetic_dataset,
    generate_synthetic_dataset,
)


def test_synthetic_dataset_structure():
    """Verify that build_synthetic_dataset outputs all required file structures."""
    dataset = build_synthetic_dataset()
    expected_files = {
        "members.json",
        "accounts.json",
        "contributions.json",
        "interactions.json",
        "digital_activity.json",
    }
    assert set(dataset.keys()) == expected_files


def test_member_schema_and_personas():
    """Verify that synthetic members comply with Pydantic schemas and include key test personas."""
    dataset = build_synthetic_dataset()
    member_data = dataset["members.json"]

    # Validate each member against MemberRecord schema
    members = [MemberRecord(**m) for m in member_data]
    member_map = {m.member_id: m for m in members}

    # Verify key test personas exist
    assert "MEM-001" in member_map, "MEM-001 (Active loyal persona) must be present"
    assert "MEM-002" in member_map, "MEM-002 (Churn risk persona) must be present"
    assert "MEM-003" in member_map, "MEM-003 (Closure inquiry persona) must be present"

    # Verify closure inquiry flags
    assert member_map["MEM-001"].has_closure_inquiry is False
    assert member_map["MEM-002"].has_closure_inquiry is False
    assert member_map["MEM-003"].has_closure_inquiry is True


def test_no_real_pii_present():
    """Verify synthetic records do not contain TFNs, BSBs, or unmasked sensitive PII."""
    dataset = build_synthetic_dataset()
    raw_str = json.dumps(dataset)

    # Check for prohibited terms and patterns
    assert "tax file number" not in raw_str.lower()
    assert "tfn" not in raw_str.lower()
    assert "bsb" not in raw_str.lower()
    assert "bank_account" not in raw_str.lower()


def test_generate_synthetic_dataset_writes_files(tmp_path: Path):
    """Verify generate_synthetic_dataset writes valid JSON files to disk."""
    out_dir = generate_synthetic_dataset(tmp_path)
    assert (out_dir / "members.json").exists()
    assert (out_dir / "accounts.json").exists()
    assert (out_dir / "contributions.json").exists()
    assert (out_dir / "interactions.json").exists()
    assert (out_dir / "digital_activity.json").exists()

    with open(out_dir / "members.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        assert len(data) >= 3
