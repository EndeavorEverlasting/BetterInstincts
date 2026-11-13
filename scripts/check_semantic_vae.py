"""Semantic VAE contract and storage defaults regression checker."""
from __future__ import annotations

import json
from pathlib import Path
from betterinstincts.semantic_vae import empty_model, SemanticVAEError
ROOT = Path(__file__).resolve().parents[1]


def check() -> None:
    contract = json.loads((ROOT / "contracts/semantic-vae.v1.json").read_text())
    settings = json.loads((ROOT / "contracts/installation-profiles.v1.json").read_text())
    assert contract["schema"] == "betterinstincts.semantic-vae/v1"
    assert contract["shape"]["latent"] == 4
    assert contract["shape"]["flattened"] == 75
    assert contract["learning"]["remote_exchange"] is False
    assert contract["learning"]["auto_collect"] is False
    assert contract["learning"]["opt_in_default"] is False
    assert contract["execute_allowed"] is False
    assert settings["defaults"]["learning.semantic_vae"] is False
    for path in (
        contract["owner"],
        contract["input_owner"].split("#")[0],
        contract["identity_owner"].split("#")[0],
        "docs/SEMANTIC_VAE.md", "tests/test_semantic_vae.py",
        "contracts/consultations/BI-LOCAL-SEMANTIC-VAE-20261113.v1.json",
        "contracts/native-gameplay-decisions/BI-LOCAL-SEMANTIC-VAE-20261113.v1.json",
    ):
        assert (ROOT / path).is_file(), path
    try:
        empty_model({})
    except SemanticVAEError:
        pass
    else:
        raise AssertionError("UNVERIFIED_WORLD_CONTEXT_ADMITTED")


if __name__ == "__main__":
    check()
    print("SEMANTIC_VAE_OFFLINE_STORAGE_AND_CONSENT_CONTRACT_PASS")
