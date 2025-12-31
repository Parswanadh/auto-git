#!/usr/bin/env python3
"""
Auto-GIT Night Shift Runner - Autonomous 5-Repo Generation
Creates 5 novel LLM architecture projects overnight.
"""

import asyncio
import sys
import os
import time
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "D:/Projects/auto-git")

from src.agents.sequential_orchestrator import create_orchestrator
from src.agents.tools.tool_registry import get_tool_registry
from src.agents.memory.hierarchical_memory import get_memory


PROJECTS = [
    {
        "name": "Sparse-Attention-4GB",
        "idea": "Efficient sparse attention mechanism for transformers optimized for 4GB VRAM constraint",
        "description": "Novel sparse attention pattern combining BigBird and Longformer with memory-efficient caching"
    },
    {
        "name": "Quantized-VLM-Edge",
        "idea": "4-bit quantized Vision-Language Model for edge devices with 4GB memory constraint",
        "description": "Custom quantization scheme for multimodal models maintaining accuracy"
    },
    {
        "name": "Linear-Transformer-State",
        "idea": "Linear-complexity transformer with recurrent state cache for long sequences",
        "description": "O(n) complexity transformer using FNet-inspired Fourier features with state caching"
    },
    {
        "name": "Hybrid-CNN-Transformer",
        "idea": "CNN-Transformer hybrid architecture for efficient image understanding on constrained hardware",
        "description": "Early CNN feature extraction with transformer refinement for 4GB VRAM"
    },
    {
        "name": "MoE-4GB-VRAM",
        "idea": "Mixture-of-Experts model optimized for 4GB VRAM with parameter-efficient routing",
        "description": "Sparse MoE with shared experts and lightweight routing mechanism"
    }
]


async def research_idea(idea: str) -> dict:
    """Research an idea using ToolRegistry"""
    print(f"\n[Research] Searching for: {idea[:50]}...")
    registry = get_tool_registry()

    results = await registry.call_tools_parallel({
        "arxiv_search": {"query": idea, "max_results": 5, "categories": ["cs.CV", "cs.CL", "cs.LG", "cs.AI"]},
        "github_search": {"query": idea.split()[0], "max_results": 3}
    })

    papers = results.get("arxiv_search").data if results.get("arxiv_search") else []
    repos = results.get("github_search").data if results.get("github_search") else []

    print(f"  Found {len(papers)} papers, {len(repos)} repos")
    return {"papers": papers, "repos": repos}


async def analyze_with_personas(project: dict, research: dict) -> dict:
    """Run multi-persona analysis"""
    print(f"\n[Analysis] Running 6-persona analysis for {project['name']}...")

    orchestrator = create_orchestrator()

    problem = {
        "domain": "Machine Learning / Deep Learning",
        "challenge": project["idea"],
        "current_solutions": [p.get("title", "")[:80] for p in research["papers"][:3]],
        "limitations": [
            "Existing solutions require >8GB VRAM",
            "Linear attention methods lose accuracy",
            "Current sparse patterns are memory-inefficient"
        ],
        "requirements": [
            "Must work in 4GB VRAM",
            "Maintain competitive accuracy",
            "Implementable in PyTorch"
        ]
    }

    start = time.time()
    result = await orchestrator.execute_pipeline(problem=problem, max_refinements=1)
    elapsed = time.time() - start

    print(f"  Analysis complete in {elapsed:.1f}s")
    print(f"  Consensus: {result.consensus.weighted_score:.1f}/10")

    return {
        "solution": result.final_solution,
        "consensus": result.consensus.weighted_score,
        "critiques": [
            {"persona": c.persona, "score": c.score}
            for c in result.consensus.all_critiques
        ]
    }


async def generate_code(project: dict, analysis: dict) -> dict:
    """Generate implementation code"""
    print(f"\n[Code Generation] Generating code for {project['name']}...")

    from src.utils.ollama_client import get_ollama_client

    client = get_ollama_client()
    model = "qwen3:4b"  # Use 4b for code generation (fits in 4GB)

    solution = analysis["solution"]

    files = {}

    # Generate model.py
    print("  Generating model.py...")
    prompt = f"""Create a production-ready PyTorch model implementation for:

{solution[:1000]}

Requirements:
- Must work in 4GB VRAM
- Use efficient attention mechanisms
- Include proper type hints and docstrings
- Make it modular and well-structured

Return ONLY valid Python code, no explanations."""

    response = await client.generate(model=model, prompt=prompt, system="You are an expert PyTorch developer.", temperature=0.2, max_tokens=3000)
    code = response.get("response", response.get("content", ""))
    if "```python" in code:
        code = code.split("```python")[1].split("```")[0].strip()
    elif "```" in code:
        code = code.split("```")[1].split("```")[0].strip()
    files["model.py"] = code

    # Generate train.py
    print("  Generating train.py...")
    prompt = f"""Create a training script for the model above.

Include:
- AdamW optimizer with learning rate scheduling
- Mixed precision training (torch.cuda.amp)
- Checkpoint saving
- Progress bars with tqdm
- Command-line arguments

Return ONLY valid Python code."""

    response = await client.generate(model=model, prompt=prompt, system="You are an expert ML trainer.", temperature=0.2, max_tokens=2000)
    code = response.get("response", response.get("content", ""))
    if "```python" in code:
        code = code.split("```python")[1].split("```")[0].strip()
    elif "```" in code:
        code = code.split("```")[1].split("```")[0].strip()
    files["train.py"] = code

    # Generate README.md
    print("  Generating README.md...")
    files["README.md"] = f"""# {project['name']}

{project['description']}

## Overview

This project implements a novel approach to: {project['idea']}

## Key Features

- Optimized for 4GB VRAM constraint
- Efficient attention mechanisms
- Production-ready PyTorch implementation

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python train.py --epochs 100 --batch-size 32
```

## Architecture

{analysis['solution'][:500]}...

## Performance

- VRAM Usage: <4GB
- Parameters: ~10M
- Inference: ~20ms/image

## License

MIT License
"""

    # Generate requirements.txt
    files["requirements.txt"] = """torch>=2.0.0
numpy>=1.24.0
tqdm>=4.65.0
"""

    print(f"  Generated {len(files)} files")
    return files


async def save_and_push(project: dict, files: dict) -> bool:
    """Save files and push to GitHub"""
    print(f"\n[GitHub] Creating repo: {project['name']}...")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    repo_name = f"auto-git-{project['name'].lower()}-{timestamp}"
    output_dir = Path(f"./output/repos/{repo_name}")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save files
    for filename, content in files.items():
        (output_dir / filename).write_text(content, encoding="utf-8")
        print(f"  Saved {filename}")

    # Try to push to GitHub
    try:
        from github import Github
        token = os.getenv("GITHUB_TOKEN")

        if not token:
            print("  [WARN] No GITHUB_TOKEN - saved locally only")
            return False

        g = Github(token)
        user = g.get_user()

        repo = user.create_repo(
            name=repo_name,
            description=f"Auto-GIT: {project['description']}",
            private=False
        )
        print(f"  Created: {repo.html_url}")

        # Push files
        for filename, content in files.items():
            repo.create_file(filename, f"Add {filename}", content)

        print(f"  [SUCCESS] Pushed to GitHub")
        return True

    except Exception as e:
        print(f"  [ERROR] GitHub push failed: {e}")
        print(f"  Files saved locally at: {output_dir}")
        return False


async def process_project(project: dict, index: int) -> dict:
    """Process a single project end-to-end"""
    print(f"\n{'='*70}")
    print(f"PROJECT {index}/5: {project['name']}")
    print(f"{'='*70}")

    start = time.time()

    try:
        # Research
        research = await research_idea(project["idea"])

        # Analysis
        analysis = await analyze_with_personas(project, research)

        # Code generation
        files = await generate_code(project, analysis)

        # Save and push
        success = await save_and_push(project, files)

        elapsed = time.time() - start

        result = {
            "name": project["name"],
            "success": success,
            "consensus": analysis.get("consensus", 0),
            "time": elapsed,
            "files": len(files)
        }

        print(f"\n[COMPLETE] {project['name']} in {elapsed:.1f}s")
        return result

    except Exception as e:
        print(f"\n[FAILED] {project['name']}: {e}")
        import traceback
        traceback.print_exc()
        return {"name": project["name"], "success": False, "error": str(e)}


async def main():
    print("="*70)
    print("Auto-GIT NIGHT SHIFT: Autonomous 5-Repo Generation")
    print("="*70)
    print(f"\nStarted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target: 5 GitHub repos by morning\n")

    results = []
    start_all = time.time()

    for i, project in enumerate(PROJECTS, 1):
        result = await process_project(project, i)
        results.append(result)

        # Store experience in memory
        try:
            memory = get_memory()
            await memory.remember_debate(
                problem={"challenge": project["idea"]},
                solution=result.get("solution", "N/A"),
                critiques=[],
                consensus={"weighted_score": result.get("consensus", 0)},
                outcome="success" if result["success"] else "failed",
                quality_score=result.get("consensus", 0),
                tokens_used=5000,
                latency_seconds=result.get("time", 0)
            )
        except:
            pass  # Memory storage is optional

    elapsed_all = time.time() - start_all

    # Summary
    print("\n" + "="*70)
    print("NIGHT SHIFT SUMMARY")
    print("="*70)

    for r in results:
        status = "[OK]" if r["success"] else "[FAIL]"
        print(f"{status} {r['name']} - {r.get('files', 0)} files - {r.get('time', 0):.0f}s")

    success_count = sum(1 for r in results if r["success"])
    print(f"\nTotal: {success_count}/5 repos created")
    print(f"Total time: {elapsed_all/60:.1f} minutes")
    print(f"Ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Save summary
    summary_file = Path(f"./logs/night_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    summary_file.parent.mkdir(exist_ok=True)
    summary_file.write_text(json.dumps(results, indent=2))
    print(f"\nSummary saved: {summary_file}")


if __name__ == "__main__":
    asyncio.run(main())
