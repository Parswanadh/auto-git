import pytest

from src.utils.feature_verifier import (
    FALLBACK_MARKER,
    FeatureVerifier,
    is_generation_fallback_only_failure,
)


pytestmark = pytest.mark.unit


def test_hardening_removes_self_import_and_rewrites_id_lookup():
    script = """
_RESULTS = []

from feature_tests import _RESULTS, feature_test, run_all_tests

def test_case():
    task_data = None
    task_id = task_data[\"id\"]
"""

    hardened = FeatureVerifier._harden_generated_feature_tests(script)

    assert "from feature_tests import" not in hardened
    assert "task_id = _require_id(task_data, 'task_data')" in hardened
    assert "def _require_id(" in hardened


def test_hardening_uses_safe_cleanup_and_storage_dispose():
    script = """
import os

_RESULTS = []

def test_case():
    storage = object()
    db_name = \"tmp.db\"
    if os.path.exists(db_name):
        os.remove(db_name)
"""

    hardened = FeatureVerifier._harden_generated_feature_tests(script)

    assert "def _safe_remove_file(" in hardened
    assert "def _safe_dispose_storage(" in hardened
    assert "os.remove(" not in hardened
    assert "os.unlink(path)" in hardened
    assert "_safe_remove_file(path)" not in hardened
    assert "_safe_dispose_storage(locals().get('storage'))" in hardened
    assert "_safe_remove_file(db_name)" in hardened


def test_fallback_script_embeds_generation_marker():
    verifier = FeatureVerifier()
    script = verifier._fallback_test_script({"key_features": ["auth"]})
    assert FALLBACK_MARKER in script


def test_generation_fallback_only_failure_detected():
    report = {
        "test_generation_fallback": True,
        "features": [
            {
                "status": "FAIL",
                "error": f"{FALLBACK_MARKER}: UNTESTED test generation syntax error",
                "output": "",
            },
            {
                "status": "ERROR",
                "error": f"{FALLBACK_MARKER}: another fallback failure",
                "output": "",
            },
        ],
    }
    assert is_generation_fallback_only_failure(report) is True


def test_generation_fallback_only_failure_rejects_real_failures():
    report = {
        "test_generation_fallback": True,
        "features": [
            {
                "status": "FAIL",
                "error": "assertion failed: todo count mismatch",
                "output": "",
            }
        ],
    }
    assert is_generation_fallback_only_failure(report) is False
