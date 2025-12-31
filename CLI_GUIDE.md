# 🚀 AUTO-GIT CLI - Quick Reference Guide

## ✅ Implementation Complete!

All systems operational and tested. Full LangGraph-powered pipeline with professional CLI.

---

## 📋 System Overview

**Status**: ✅ Production Ready  
**Architecture**: LangGraph StateGraph  
**Models**: qwen3:4b (debate), deepseek-coder-v2:16b (code gen)  
**Features**: Progress bars, real-time monitoring, sequential execution

---

## 🎮 Usage

### 1. Show Main Menu
```bash
python auto_git_cli.py
# or
python auto_git_cli.py menu
```

### 2. Generate Code from Research Idea
```bash
# Basic usage
python auto_git_cli.py generate "Your research idea here"

# With options
python auto_git_cli.py generate "Sparse attention" --rounds 2 --no-search

# With GitHub publishing
python auto_git_cli.py generate "Efficient transformers" --github
```

**Options:**
- `--rounds, -r <N>`: Number of debate rounds (default: 2)
- `--search/--no-search`: Enable/disable web search (default: enabled)
- `--github, -g`: Auto-publish to GitHub
- `--output, -o <dir>`: Custom output directory

### 3. Research-Only Mode
```bash
python auto_git_cli.py research "Transformer attention mechanisms"

# Limit results
python auto_git_cli.py research "Neural networks" --max 10
```

### 4. Run Multi-Perspective Debate
```bash
python auto_git_cli.py debate "Your research problem" --rounds 3
```

### 5. Check System Status
```bash
python auto_git_cli.py status
```

### 6. Configure Settings
```bash
# Set GitHub token
python auto_git_cli.py config --github-token ghp_xxxxxxxxxxxxx

# Set custom Ollama URL
python auto_git_cli.py config --ollama-url http://localhost:11434
```

---

## 🎯 Pipeline Stages

The complete pipeline executes sequentially:

```
1. 🔍 Research
   ├─ arXiv paper search
   ├─ DuckDuckGo web search
   └─ GitHub implementation search

2. 🎯 Problem Extraction
   ├─ Analyze research
   ├─ Identify novel problems
   └─ Select primary problem

3. 💡 Multi-Perspective Debate
   ├─ ML Researcher proposes
   ├─ Systems Engineer proposes
   ├─ Applied Scientist proposes
   ├─ Cross-perspective critique
   ├─ Consensus check
   └─ Repeat if no consensus

4. 🏆 Solution Selection
   ├─ Evaluate all proposals
   ├─ Consider all critiques
   └─ Select best approach

5. 💻 Code Generation (DeepSeek Coder)
   ├─ model.py
   ├─ train.py
   ├─ evaluate.py
   ├─ data_loader.py
   ├─ utils.py
   ├─ README.md
   └─ requirements.txt

6. 📤 GitHub Publishing
   ├─ Create repository
   ├─ Upload all files
   └─ Publish (or save locally)
```

---

## 📊 Inter-Stage Outputs

After each stage, you'll see:

### Research Results
```
┌─────────────────────────────────────┐
│ 📚 Research Results                 │
├─────────┬──────┬────────────────────┤
│ Type    │Count │ Details            │
├─────────┼──────┼────────────────────┤
│ Papers  │  5   │ Found on arXiv     │
│ Web     │  3   │ Implementations    │
└─────────┴──────┴────────────────────┘
```

### Extracted Problems
```
🎯 Extracted 3 Research Problems

1. Problem 1: Dynamic sparsity adjustment...
2. Problem 2: Efficient streaming attention...
3. Problem 3: Distribution robustness...

✓ Selected: Problem 1
```

### Debate Round
```
💡 Round 1 - 3 Proposals, 6 Critiques

1. Dynamic Sparsity Scheduler
   Perspective: Systems Engineer
   Novelty: 0.85 | Feasibility: 0.90
```

### Selected Solution
```
╔══════════════════════════════════════╗
║ 🏆 SELECTED SOLUTION                 ║
║                                      ║
║ Dynamic Sparsity Scheduler (DSS)     ║
║ ...                                  ║
╚══════════════════════════════════════╝
```

### Generated Code
```
💻 Generated Code

✓ model.py (120 lines)
✓ train.py (95 lines)
✓ evaluate.py (80 lines)
...
```

### GitHub Result
```
╔═══════════════════════════════════════╗
║ 🚀 Published to GitHub!               ║
║                                       ║
║ Repository: autogit-dss-20251226      ║
║ URL: https://github.com/...           ║
╚═══════════════════════════════════════╝
```

---

## ⚙️ Configuration

### Required
- **Ollama**: Running on localhost:11434
- **Models**: qwen3:4b, deepseek-coder-v2:16b

### Optional
- **GitHub Token**: For auto-publishing
  ```bash
  export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
  # or
  python auto_git_cli.py config --github-token ghp_xxxx
  ```

### Check Configuration
```bash
python auto_git_cli.py status
```

Output:
```
✅ Ollama running (16 models available)
✅ qwen3:4b available
✅ deepseek-coder-v2:16b available
⚠️  GitHub token not set
✅ src/langraph_pipeline/
✅ src/utils/
✅ output/
```

---

## 🎨 Progress Monitoring

Real-time progress bar shows:
- Current stage (🔍 🎯 💡 🔍 ⚖️ 🏆 💻 📤)
- Progress percentage
- Time elapsed
- Visual spinner

Example:
```
⠹ 💻 Generating code with DeepSeek... ━━━━━━━╸━━━━━━━  75% 0:08:23
```

---

## 🚨 Sequential Execution

**Important**: Pipeline runs sequentially to avoid Ollama model conflicts:

1. Research & Problem Extraction: `qwen3:4b`
2. Debate (all rounds): `qwen3:4b`  
3. Solution Selection: `qwen3:4b`
4. **[Models switch]**
5. Code Generation: `deepseek-coder-v2:16b`
6. GitHub Publishing: No LLM

Only DeepSeek Coder runs during code generation phase!

---

## 📁 Output Structure

Generated code saves to:
```
output/
  ├─ {approach-name}/
  │   └─ {timestamp}/
  │       ├─ model.py
  │       ├─ train.py
  │       ├─ evaluate.py
  │       ├─ data_loader.py
  │       ├─ utils.py
  │       ├─ README.md
  │       └─ requirements.txt
```

---

## 🐛 Troubleshooting

### Ollama Not Running
```bash
# Start Ollama
ollama serve

# Verify models
ollama list
```

### Model Not Found
```bash
# Pull required models
ollama pull qwen3:4b
ollama pull deepseek-coder-v2:16b
```

### GitHub Publishing Failed
- Check token: `echo $GITHUB_TOKEN`
- Files still saved locally in `output/`
- Set token: `export GITHUB_TOKEN=ghp_xxx`

### Import Errors
```bash
# Reinstall in conda env
conda activate auto-git
pip install -r requirements.txt
```

---

## 🎯 Example Workflows

### Quick Code Generation (No Search)
```bash
python auto_git_cli.py generate "Sparse attention" --no-search --rounds 1
```
- ⚡ Fastest option
- Skips web search
- Single debate round
- ~10-15 minutes total

### Full Research Pipeline
```bash
python auto_git_cli.py generate "Novel transformer architecture" --rounds 3
```
- 🔍 Full web search
- 3 debate rounds
- Comprehensive evaluation
- ~30-45 minutes total

### Research + GitHub Publishing
```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
python auto_git_cli.py generate "Efficient NLP models" --github --rounds 2
```
- Full pipeline
- Auto-publish to GitHub
- Creates public repository
- ~20-30 minutes total

### Debate-Only (No Code)
```bash
python auto_git_cli.py debate "Scalable attention mechanisms" --rounds 3
```
- Multi-perspective analysis
- No code generation
- Just debate results
- ~15-20 minutes

---

## 📊 Performance

**Typical Timings** (on local hardware):

| Stage                | Time (1 round) | Time (3 rounds) |
|----------------------|----------------|-----------------|
| Research             | 10-30s         | 10-30s          |
| Problem Extraction   | 1-2min         | 1-2min          |
| Solution Generation  | 2-3min         | 6-9min          |
| Critique             | 3-4min         | 9-12min         |
| Consensus Check      | <1s            | <1s             |
| Solution Selection   | 1-2min         | 1-2min          |
| Code Generation      | 8-12min        | 8-12min         |
| GitHub Publishing    | 5-10s          | 5-10s           |
| **Total**            | **15-25min**   | **25-40min**    |

---

## 🎓 Advanced Usage

### Custom Output Directory
```bash
python auto_git_cli.py generate "Your idea" --output ./my-projects
```

### Help for Any Command
```bash
python auto_git_cli.py generate --help
python auto_git_cli.py research --help
python auto_git_cli.py config --help
```

### Stop After Specific Stage (Debug)
Edit `auto_git_cli.py` and add:
```python
result = asyncio.run(run_auto_git_pipeline(
    idea=idea,
    stop_after="solution_selection"  # Stop before code gen
))
```

---

## 🏗️ Architecture

```
auto_git_cli.py          # Entry point
    ↓
workflow_enhanced.py     # Progress monitoring + routing
    ↓
nodes.py                 # 8 LangGraph nodes
    ├─ research_node
    ├─ problem_extraction_node
    ├─ solution_generation_node
    ├─ critique_node
    ├─ consensus_check_node
    ├─ solution_selection_node
    ├─ code_generation_node      # ⭐ DeepSeek Coder
    └─ git_publishing_node       # ⭐ PyGithub
```

---

## 🚀 Production Ready Features

✅ **CLI Tool**: Professional interface with ASCII art  
✅ **Progress Bars**: Real-time progress with Rich  
✅ **Inter-Stage Output**: See results at each step  
✅ **Sequential Execution**: No model conflicts  
✅ **Error Handling**: Graceful failures with fallbacks  
✅ **Local Fallback**: Saves locally if GitHub fails  
✅ **Comprehensive Logging**: Track everything  
✅ **Type Safety**: Full TypedDict state management  
✅ **Checkpointing**: Resume from failures  
✅ **Modular Design**: Easy to extend  

---

## 📝 Next Steps

1. **Set GitHub Token** (optional):
   ```bash
   export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
   ```

2. **Run Your First Pipeline**:
   ```bash
   python auto_git_cli.py generate "Your amazing research idea"
   ```

3. **Check Output**:
   ```bash
   ls output/
   ```

4. **Visit GitHub** (if published):
   - Check your GitHub profile for new repository!

---

## 🎉 Success!

You now have a production-grade, LangGraph-powered pipeline that:
- Researches papers automatically
- Debates solutions from multiple perspectives
- Generates working PyTorch code
- Publishes to GitHub

**All with beautiful CLI progress monitoring!** 🚀

---

*Built with LangGraph, Ollama, and ❤️*
