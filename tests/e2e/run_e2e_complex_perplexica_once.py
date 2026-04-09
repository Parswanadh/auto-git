"""Run one complex E2E pipeline test with Perplexica enabled for this process only."""

import asyncio
import json
import os
import sys
import time
import traceback
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Keep terminal output parse-friendly
os.environ["NO_COLOR"] = "1"
os.environ["TERM"] = "dumb"

# Hard safety guard: never use local models on this runner.
# This protects shared GPU sessions from Ollama/local model launches.
os.environ["AUTOGIT_DISABLE_LOCAL_MODELS"] = "true"
os.environ["AUTOGIT_LOCAL_MODELS_ENABLED"] = "false"
if "PERPLEXICA_ENABLED" not in os.environ:
    os.environ["PERPLEXICA_ENABLED"] = "true"
if "AUTOGIT_RESEARCH_TOPIC_MAX_CHARS" not in os.environ:
    os.environ["AUTOGIT_RESEARCH_TOPIC_MAX_CHARS"] = "700"
if "AUTOGIT_SOTA_TIMEOUT_S" not in os.environ:
    os.environ["AUTOGIT_SOTA_TIMEOUT_S"] = "300"
if "AUTOGIT_MAX_FIX_ATTEMPTS_CAP" not in os.environ:
    os.environ["AUTOGIT_MAX_FIX_ATTEMPTS_CAP"] = "8"

from dotenv import load_dotenv

load_dotenv()


def _ensure_dirs() -> tuple[Path, Path]:
    out_dir = Path("output") / "e2e_complex_perplexica"
    out_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    return out_dir, logs_dir


async def main() -> int:
    out_dir, logs_dir = _ensure_dirs()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_path = out_dir / f"complex_run_result_{stamp}.json"
    summary_path = out_dir / f"complex_run_summary_{stamp}.txt"

    complex_idea = (
        "Build a production-grade privacy-preserving federated learning platform for "
        "multihospital ICU mortality prediction with robust concept-drift handling and "
        "adversarial resilience. Requirements: asynchronous FastAPI control-plane; client "
        "simulator for 10+ hospitals with heterogeneous feature schemas and missingness; "
        "secure aggregation protocol; differential privacy accounting with epsilon budget "
        "tracking per round; drift detection (population + label + calibration drift) with "
        "automatic rollback/retraining policy; uncertainty-aware inference with conformal "
        "prediction; model registry/versioning; reproducible experiment runner; complete "
        "Docker Compose stack (API, worker, redis, postgres); full pytest suite for unit and "
        "integration paths; CLI for training, evaluation, and incident simulation; comprehensive "
        "README with architecture, threat model, and operations runbook."
    )

    print("=" * 80)
    print("COMPLEX E2E RUN (CLOUD-ONLY, LOCAL MODELS DISABLED)")
    print("=" * 80)
    print(f"idea_length={len(complex_idea)}")
    print(f"output_dir={out_dir}")
    print(f"result_path={result_path}")
    print(f"AUTOGIT_DISABLE_LOCAL_MODELS={os.environ.get('AUTOGIT_DISABLE_LOCAL_MODELS')}")
    print(f"PERPLEXICA_ENABLED={os.environ.get('PERPLEXICA_ENABLED')}")
    print(f"AUTOGIT_RESEARCH_TOPIC_MAX_CHARS={os.environ.get('AUTOGIT_RESEARCH_TOPIC_MAX_CHARS')}")
    print(f"AUTOGIT_SOTA_TIMEOUT_S={os.environ.get('AUTOGIT_SOTA_TIMEOUT_S')}")

    start = time.time()
    try:
        from src.langraph_pipeline.workflow_enhanced import run_auto_git_pipeline

        result = await run_auto_git_pipeline(
            idea=complex_idea,
            use_web_search=True,
            max_debate_rounds=2,
            auto_publish=False,
            output_dir=str(out_dir / "generated_project"),
            thread_id=f"complex_perplexica_{stamp}",
            resume=False,
        )

        elapsed = time.time() - start

        if not isinstance(result, dict):
            result = {"raw_result": str(result)}

        result["_meta"] = {
            "elapsed_s": round(elapsed, 2),
            "timestamp": stamp,
            "perplexica_enabled": os.environ.get("PERPLEXICA_ENABLED"),
            "perplexica_mode": os.environ.get("PERPLEXICA_MODE"),
            "perplexica_swarm": os.environ.get("PERPLEXICA_SWARM"),
            "perplexica_url": os.environ.get("PERPLEXICA_URL"),
            "idea": complex_idea,
        }

        result_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

        rc = result.get("research_context") if isinstance(result, dict) else {}
        px = rc.get("perplexica_research") if isinstance(rc, dict) else {}
        debates = result.get("debate_rounds") if isinstance(result, dict) else []
        files = result.get("generated_code", {}) if isinstance(result, dict) else {}
        file_count = len(files) if isinstance(files, dict) else 0
        quality_gate = result.get("quality_gate") if isinstance(result.get("quality_gate"), dict) else {}
        hard_failures = result.get("hard_failures", []) if isinstance(result.get("hard_failures"), list) else []
        top_errors = result.get("errors", []) if isinstance(result.get("errors"), list) else []
        test_results = result.get("test_results") if isinstance(result.get("test_results"), dict) else {}
        exec_errors = test_results.get("execution_errors", []) if isinstance(test_results.get("execution_errors"), list) else []
        hard_failure_count = int(quality_gate.get("hard_failures_count", len(hard_failures)) or 0)
        derived_error_count = max(len(top_errors), len(exec_errors), hard_failure_count)

        summary_lines = [
            f"elapsed_s={elapsed:.2f}",
            f"current_stage={result.get('current_stage')}",
            f"tests_passed={result.get('tests_passed')}",
            f"correctness_passed={quality_gate.get('correctness_passed')}",
            f"self_eval_score={result.get('self_eval_score')}",
            f"goal_eval_present={bool(result.get('goal_eval_report'))}",
            f"error_count={derived_error_count}",
            f"execution_error_count={len(exec_errors)}",
            f"hard_failures_count={hard_failure_count}",
            f"publish_eligible={quality_gate.get('publish_eligible')}",
            f"debate_rounds={len(debates) if isinstance(debates, list) else 'n/a'}",
            f"generated_file_count={file_count}",
            f"perplexica_status={px.get('status') if isinstance(px, dict) else 'missing'}",
            f"perplexica_source_count={len(px.get('sources', [])) if isinstance(px, dict) and isinstance(px.get('sources', []), list) else 0}",
            f"result_json={result_path}",
        ]
        if hard_failures:
            summary_lines.append("hard_failures_top3=")
            summary_lines.extend([f"  - {msg}" for msg in hard_failures[:3]])
        summary_text = "\n".join(summary_lines)
        summary_path.write_text(summary_text + "\n", encoding="utf-8")

        print("RUN_COMPLETE")
        print(summary_text)
        return 0

    except Exception as exc:
        elapsed = time.time() - start
        fail = {
            "elapsed_s": round(elapsed, 2),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
        result_path.write_text(json.dumps(fail, indent=2), encoding="utf-8")
        print("RUN_CRASHED")
        print(json.dumps(fail, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
