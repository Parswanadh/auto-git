#!/usr/bin/env python3
"""Quick verification of all middleware components."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from src.utils.middleware import (
    LoopDetector, get_loop_detector, reset_loop_detector,
    run_pre_completion_checklist, format_checklist_report,
    run_state_compaction,
    offload_large_output,
    extract_error_context, build_focused_fix_prompt,
    compose_middleware,
)

passed = 0
total = 7

# 1. LoopDetector
reset_loop_detector()
ld = get_loop_detector()
for i in range(6):
    w = ld.record_file_edit("main.py")
assert w is not None, "Should warn after 5 edits"
for _ in range(4):
    ld.record_error("nameerror foo")
ctx = ld.get_context_injection()
assert "main.py" in ctx, "Context should mention hot file"
passed += 1
print("  [1/7] LoopDetector: OK")

# 2. PreCompletion Checklist — good state
state = {
    "generated_code": {"files": {
        "main.py": (
            "import os\nimport sys\n\n"
            "def main():\n    print('Hello World')\n\n"
            'if __name__ == "__main__":\n    main()\n'
        ),
        "utils.py": "def add(a, b):\n    return a + b\n",
        "requirements.txt": "requests>=2.28\nfastapi>=0.100\n",
        "README.md": "# My Project\n\nThis is a project.\n",
    }},
    "tests_passed": True,
    "self_eval_score": 7.5,
    "smoke_test": {"passed": True},
}
items = run_pre_completion_checklist(state)
report = format_checklist_report(items)
errors = [i for i in items if not i.passed and i.severity == "error"]
assert len(errors) == 0, f"Unexpected errors: {[(e.name, e.details) for e in errors]}"
passed += 1
print("  [2/7] PreCompletion Checklist: OK")

# 3. State Compaction
big = {
    "errors": ["err_" + str(i) for i in range(50)],
    "warnings": ["warn_" + str(i) for i in range(30)],
    "fix_diffs": list(range(10)),
    "resource_events": list(range(20)),
}
result = run_state_compaction(big)
assert len(result["errors"]) <= 16, f"Errors not compacted: {len(result['errors'])}"
assert len(result["warnings"]) <= 11
assert len(result["fix_diffs"]) <= 3
assert len(result["resource_events"]) <= 10
passed += 1
print("  [3/7] State Compaction: OK")

# 4. Output Offloading
assert offload_large_output("short", "test") == "short"
big_out = offload_large_output("x" * 5000, "test_big")
assert len(big_out) < 5000, "Should truncate large output"
assert "offloaded" in big_out.lower(), "Should mention offload file"
passed += 1
print("  [4/7] Output Offloading: OK")

# 5. Error Context Extraction
code = (
    "import os\n\n"
    "def foo():\n"
    "    x = 1\n"
    "    y = 2\n"
    "    return x + z\n\n"
    "def bar():\n"
    "    return 42\n"
)
ctx_code, start, end = extract_error_context(code, 6)
assert "foo" in ctx_code or "return" in ctx_code
passed += 1
print("  [5/7] Error Context Extraction: OK")

# 6. Focused Fix Prompt
prompt = build_focused_fix_prompt("main.py", code, [{"line": 6, "message": "NameError: z"}])
assert "main.py" in prompt
passed += 1
print("  [6/7] Focused Fix Prompt: OK")

# 7. Bad State Detection
bad_state = {
    "generated_code": {"files": {
        "empty.py": "",
        "broken.py": "def x(:\n    pass\n",
    }}
}
bad_items = run_pre_completion_checklist(bad_state)
bad_errors = [i for i in bad_items if not i.passed and i.severity == "error"]
assert len(bad_errors) >= 2, f"Should catch empty + syntax: {[(e.name, e.details) for e in bad_errors]}"
passed += 1
print("  [7/7] Bad State Detection: OK")

print(f"\n{'='*50}")
print(f"  ALL {passed}/{total} MIDDLEWARE TESTS PASSED")
print(f"{'='*50}")
