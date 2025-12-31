"""
Quick test for integrated workflow - structure and nodes only (no full pipeline).
"""

import asyncio
import sys
sys.path.insert(0, "D:/Projects/auto-git")

from src.langraph_pipeline.integrated_workflow import (
    build_integrated_workflow,
    compile_integrated_workflow,
    print_integrated_workflow_structure
)
from src.utils.logger import get_logger

logger = get_logger("test_integrated_quick")


async def main():
    print("\n" + "=" * 70)
    print("QUICK INTEGRATED WORKFLOW TEST")
    print("=" * 70)

    # Test 1: Build workflow
    print("\n[Step 1] Building workflow...")
    workflow = build_integrated_workflow()
    print("[OK] Workflow built successfully")

    # Test 2: Compile workflow
    print("\n[Step 2] Compiling workflow...")
    compiled = compile_integrated_workflow()
    print("[OK] Workflow compiled successfully")

    # Test 3: Print structure
    print("\n[Step 3] Printing workflow structure...")
    print_integrated_workflow_structure()

    print("\n" + "=" * 70)
    print("[SUCCESS] Quick test passed!")
    print("=" * 70)

    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
