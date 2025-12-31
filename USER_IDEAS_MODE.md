# User Ideas Mode - Quick Start Guide

## Overview
You can now provide YOUR OWN research ideas and let the AI agents:
1. Generate novel solutions through multi-agent debate
2. Validate feasibility (hardware, datasets, implementation)
3. Generate production-ready code (coming soon)
4. Publish to GitHub (coming soon)

**No paper discovery needed** - just your idea!

## Usage

### Single Idea (Command Line)
```bash
python run.py generate --idea "Your research problem here"
```

Example:
```bash
python run.py generate --idea "Create a lightweight vision transformer with only 1M parameters for mobile deployment"
```

### Multiple Ideas (From File)
Create a text file with one idea per line:

**ideas.txt:**
```
Develop a neural network that dynamically adjusts depth based on input complexity
Create an RLHF algorithm that needs only 10% of current training data
Design an O(n) attention mechanism for transformers
```

Run:
```bash
python run.py generate --ideas-file ideas.txt
```

### Interactive Mode
```bash
python run.py generate --interactive
```

Then type your ideas one per line. Press Enter on empty line to start processing.

### Mix Multiple Sources
```bash
python run.py generate \
  --idea "First idea from command line" \
  --ideas-file more_ideas.txt \
  --interactive
```

All ideas will be collected and processed sequentially.

## What Happens

For each idea:
1. **Problem Statement Created** - Your idea becomes a structured problem
2. **Solution Generation** - AI generates 3 novel approaches
3. **Expert Critique** - AI critic evaluates each solution
4. **Debate Rounds** - Generator and critic iterate up to 3 rounds
5. **Feasibility Check** - Validates hardware, datasets, implementation
6. **Code Generation** (coming soon) - Produces production code
7. **GitHub Publish** (coming soon) - Creates repo with implementation

## Current Status

✅ **Working:**
- User idea input (single, file, interactive)
- Sequential processing of multiple ideas  
- Debate system integration
- Checkpoint saving per idea

⚠️ **In Progress:**
- JSON parsing from qwen3:8b (needs better prompts)
- Validation agent execution
- Code generation (Tier 3)
- GitHub publishing (Tier 4)

## Example Output

```
✅ Loaded 3 idea(s)
  1. Develop a neural network that dynamically adjusts depth...
  2. Create an RLHF algorithm that needs only 10% of current...
  3. Design an O(n) attention mechanism for transformers

============================================================
💡 IDEA 1/3
============================================================
Develop a neural network that dynamically adjusts depth based on input complexity

🎭 Starting debate (max 3 rounds)...
💡 Generating solutions (iteration 1)...
🔍 Critiquing solution: Adaptive Depth Network...
🔄 DEBATE ROUND 2/3
...
✅ Idea 1 validated! Ready for code generation.
```

## Tips

1. **Be Specific**: "Reduce transformer memory by 50%" is better than "Improve transformers"
2. **Include Constraints**: Mention target accuracy, size, speed, hardware
3. **One Problem Per Line**: Each idea should be a distinct research problem
4. **Start Small**: Test with 1-2 ideas first to see the debate process

## Files

- **ideas.txt** - Sample ideas file (included)
- **run.py** - Main CLI with `generate` command
- **Checkpoints** - Saved in `./data/checkpoints/` after each idea

## Next Steps

Once JSON parsing is fixed, you'll see:
- 3 solution proposals per round
- Detailed critiques with scores
- Final validated solution
- Code generation output
- GitHub repository created

---

**The idea is yours. The implementation is automated.** 🚀
