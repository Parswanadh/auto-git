"""
Run the pipeline end-to-end on a simple idea and capture all output.
No interactive prompts — purely programmatic.
"""
import sys, os, time, traceback, json

# Fix encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Disable Rich console coloring to avoid encoding issues
os.environ["NO_COLOR"] = "1"
os.environ["TERM"] = "dumb"

# Load .env
from dotenv import load_dotenv
load_dotenv()

import asyncio
import logging

# Set up logging to capture everything
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler("logs/pipeline_e2e_test.log", encoding="utf-8", mode="w"),
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger("pipeline_test")

async def run_test():
    idea = "Create a simple command-line calculator that supports add, subtract, multiply, divide"
    
    logger.info(f"=" * 60)
    logger.info(f"PIPELINE TEST RUN")
    logger.info(f"Idea: {idea}")
    logger.info(f"=" * 60)
    
    start = time.time()
    
    try:
        from src.langraph_pipeline.workflow_enhanced import run_auto_git_pipeline
        
        result = await run_auto_git_pipeline(
            idea=idea,
            use_web_search=True,
            max_debate_rounds=1,      # Keep it fast
            auto_publish=False,        # Don't push to GitHub
            output_dir="output/test_calculator",
            thread_id="test_calc_e2e_001",
            resume=False,              # Fresh run
        )
        
        elapsed = time.time() - start
        logger.info(f"\n{'=' * 60}")
        logger.info(f"PIPELINE COMPLETED in {elapsed:.1f}s")
        logger.info(f"{'=' * 60}")
        
        # Analyze results
        if result:
            logger.info(f"Result keys: {list(result.keys())}")
            logger.info(f"Current stage: {result.get('current_stage', 'UNKNOWN')}")
            logger.info(f"Errors: {result.get('errors', [])}")
            logger.info(f"Tests passed: {result.get('tests_passed', 'N/A')}")
            
            # Check generated code
            gen_code = result.get("generated_code", {})
            if isinstance(gen_code, dict):
                files = gen_code.get("files", gen_code)
                logger.info(f"Generated files: {list(files.keys()) if isinstance(files, dict) else 'N/A'}")
                for fname, content in (files.items() if isinstance(files, dict) else []):
                    lines = len(content.split('\n')) if isinstance(content, str) else 0
                    logger.info(f"  {fname}: {lines} lines")
            
            # Check GitHub
            logger.info(f"GitHub URL: {result.get('github_url', 'NOT PUBLISHED')}")
            
            # Self-eval score
            se = result.get("self_eval_score")
            if se is not None:
                logger.info(f"Self-eval score: {se}/10")
            
            # Goal eval
            ge = result.get("goal_eval_report")
            if ge:
                logger.info(f"Goal eval: {json.dumps(ge, indent=2, default=str)[:500]}")
        else:
            logger.error("Pipeline returned None/empty result!")
            
    except Exception as e:
        elapsed = time.time() - start
        logger.error(f"\nPIPELINE CRASHED after {elapsed:.1f}s")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error: {e}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(run_test())
