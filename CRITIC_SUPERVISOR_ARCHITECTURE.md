# 🎯 Critic-Generator & Supervisor Architecture

**Date**: December 26, 2025  
**Purpose**: Add self-critique, iterative refinement, and fault-tolerant orchestration

---

## 🧠 THE PROBLEM WITH CURRENT APPROACH

### Current Flow (Naive):
```
LLM generates solution → Accept it → Move on
```

**Issues:**
- ❌ No validation of solution quality
- ❌ No consideration of real-world constraints
- ❌ No iterative refinement
- ❌ First solution might not be optimal
- ❌ No error recovery if something fails

---

## ✨ ENHANCED ARCHITECTURE: CRITIC-GENERATOR DEBATE

### Concept: Multi-Agent Debate System

Instead of accepting the first solution, we create a **debate loop** where:
1. **Generator** proposes solutions
2. **Critic** finds flaws and suggests improvements
3. They iterate until reaching consensus
4. **Supervisor** orchestrates the entire process

This mimics how real research teams work!

---

## 🏗️ TIER 2.5: CRITIC-GENERATOR DEBATE SYSTEM (NEW!)

### Agent 2.5.1: Solution Generator
```yaml
Purpose: Generate novel solutions to problems
Input: ProblemStatement
Output: SolutionProposal{
  approach_name: str,
  architecture_design: str,
  key_innovations: [],
  implementation_plan: str,
  expected_performance: str,
  iteration: int                    # Which iteration is this?
}
Model: gpt-oss:20b (creative reasoning)
```

### Agent 2.5.2: Expert Critic
```yaml
Purpose: Act as expert reviewer who finds flaws
Role: "You are a senior AI researcher reviewing a proposed solution"

Input: SolutionProposal
Output: CritiqueReport{
  overall_assessment: str,          # "promising", "needs work", "flawed"
  strengths: [],                    # What's good?
  weaknesses: [],                   # What's problematic?
  technical_concerns: [],           # Implementation issues
  missing_considerations: [],       # What was overlooked?
  real_world_feasibility: float,    # 0-10: Can this actually work?
  optimization_suggestions: [],     # How to improve?
  verdict: str                      # "accept", "revise", "reject"
}

Model: gpt-oss:20b (critical reasoning)

Prompt Template:
"""
You are a senior AI researcher peer-reviewing a proposed solution.
Be thorough, critical, and constructive.

Problem: {problem_statement}
Proposed Solution: {solution_proposal}

Evaluate:
1. Technical Soundness: Is the approach theoretically valid?
2. Novelty: Is this truly different from existing work?
3. Feasibility: Can this be implemented in PyTorch realistically?
4. Efficiency: What's the computational cost?
5. Scalability: Will this work on large datasets?
6. Real-world Applicability: Is this practical?

Be harsh but fair. Find the flaws.
"""
```

### Agent 2.5.3: Debate Moderator
```yaml
Purpose: Facilitate multi-round debate between Generator and Critic
Input: ProblemStatement
Process:
  Round 1:
    - Generator proposes initial solution
    - Critic reviews and finds issues
  
  Round 2:
    - Generator addresses critiques
    - Proposes improved solution
    - Critic reviews again
  
  Round 3 (if needed):
    - Generator makes final refinements
    - Critic gives final assessment
  
  Max Rounds: 3 (prevent infinite loops)
  
Output: FinalSolution{
  solution: SolutionProposal,
  debate_history: [],              # All rounds of discussion
  consensus_reached: bool,
  confidence_score: float,         # How good is final solution?
  iterations_taken: int
}

Model: qwen3:8b (fast orchestration)

Exit Conditions:
  - Critic accepts solution (verdict="accept")
  - Max iterations reached (3)
  - Confidence score > 8.0
  - No improvements after 2 rounds
```

### Agent 2.5.4: Real-World Validator
```yaml
Purpose: Check if solution fits current world scenario
Input: FinalSolution + ProblemStatement

Validation Checks:
  1. Hardware Feasibility:
     - GPU memory requirements reasonable?
     - Training time feasible? (<48 hours on single GPU)
     - Inference speed practical?
  
  2. Dataset Availability:
     - Are required datasets public?
     - License compatible?
     - Size manageable?
  
  3. Implementation Complexity:
     - Can be coded in <2000 lines?
     - Dependencies available in PyPI?
     - No exotic requirements?
  
  4. Reproducibility:
     - Hyperparameters specified?
     - Random seed control?
     - Deterministic operations?
  
  5. Current Relevance:
     - Addresses a real problem?
     - Community will care?
     - Benchmarks available?

Output: ValidationResult{
  is_feasible: bool,
  feasibility_score: float,
  blocking_issues: [],
  warnings: [],
  recommendations: []
}

Model: qwen3:8b (practical assessment)
```

---

## 🎯 TIER 0: SUPERVISOR AGENT (NEW!)

### Purpose: God Mode - Orchestrates Everything

The **Supervisor** is the top-level agent that:
- Monitors all other agents
- Handles errors gracefully
- Manages state and checkpoints
- Can pause/resume operations
- Provides recovery mechanisms

### Agent 0.0: Pipeline Supervisor

```yaml
Purpose: Oversee entire pipeline execution
Responsibilities:
  1. Health Monitoring
  2. Error Recovery
  3. Resource Management
  4. State Checkpointing
  5. Graceful Shutdown

Components:

  1. Health Monitor:
     - Check Ollama connection every 30s
     - Monitor memory usage
     - Track token consumption
     - Detect stuck agents (timeout after 5min)
  
  2. Error Handler:
     - Catch all exceptions
     - Log to error_log.json
     - Retry failed operations (max 3 times)
     - Fallback strategies
  
  3. State Manager:
     - Checkpoint state every 5 minutes
     - Can resume from last checkpoint
     - Persist to disk: state_checkpoint.json
  
  4. Resource Manager:
     - Limit max concurrent Ollama calls (4)
     - Queue management for paper processing
     - Rate limiting (if needed)
  
  5. Circuit Breaker:
     - If 5 consecutive failures → PAUSE
     - If Ollama down → PAUSE
     - If disk full → PAUSE
     - Wait for human intervention

Output: SupervisorReport{
  status: "running" | "paused" | "error" | "completed",
  agents_status: {},              # Status of each agent
  errors_count: int,
  warnings_count: int,
  last_checkpoint: timestamp,
  next_action: str
}
```

### Supervisor State Machine

```python
class SupervisorState(Enum):
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    RECOVERING = "recovering"
    COMPLETED = "completed"
    SHUTDOWN = "shutdown"

class Supervisor:
    def __init__(self):
        self.state = SupervisorState.INITIALIZING
        self.error_count = 0
        self.max_errors = 5
        
    def execute_agent(self, agent, input_data):
        """Execute agent with error handling"""
        try:
            result = agent.run(input_data)
            self.error_count = 0  # Reset on success
            return result
            
        except OllamaConnectionError as e:
            logger.error(f"Ollama connection lost: {e}")
            self.pause_pipeline()
            self.wait_for_ollama()
            self.resume_pipeline()
            
        except TokenLimitExceeded as e:
            logger.warning(f"Token limit reached: {e}")
            self.save_checkpoint()
            self.wait_and_retry()
            
        except Exception as e:
            logger.error(f"Agent failed: {e}")
            self.error_count += 1
            
            if self.error_count >= self.max_errors:
                self.enter_error_state()
                self.save_error_report()
                self.notify_user()
                return None
            else:
                self.retry_with_backoff(agent, input_data)
    
    def pause_pipeline(self):
        """Gracefully pause operations"""
        self.state = SupervisorState.PAUSED
        self.save_checkpoint()
        logger.info("🔴 Pipeline PAUSED - awaiting recovery")
    
    def resume_pipeline(self):
        """Resume from checkpoint"""
        self.state = SupervisorState.RUNNING
        checkpoint = self.load_checkpoint()
        logger.info(f"🟢 Pipeline RESUMED from {checkpoint['timestamp']}")
        return checkpoint
    
    def circuit_breaker(self):
        """Stop everything if critical failure"""
        if self.error_count >= self.max_errors:
            logger.critical("🛑 CIRCUIT BREAKER ACTIVATED")
            self.state = SupervisorState.ERROR
            self.save_state()
            raise SystemError("Pipeline halted due to repeated failures")
```

---

## 🔄 COMPLETE FLOW WITH CRITIC & SUPERVISOR

### New Pipeline Flow:

```
┌─────────────────────────────────────────────────────────────┐
│ TIER 0: SUPERVISOR (Always Running)                         │
│ - Health monitoring                                         │
│ - Error recovery                                            │
│ - State checkpointing                                       │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ TIER 1: DISCOVERY                                           │
│ Paper Scout → Novelty Check → Priority Router              │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ TIER 2: PROBLEM EXTRACTION                                  │
│ Extract problem statement from paper                        │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ TIER 2.5: CRITIC-GENERATOR DEBATE (NEW!)                   │
│                                                             │
│  Round 1:                                                   │
│    Generator → Proposes Solution A                          │
│    Critic    → Finds flaws: X, Y, Z                         │
│                                                             │
│  Round 2:                                                   │
│    Generator → Revises to Solution B (addresses X, Y, Z)    │
│    Critic    → Still concerned about Y, suggests fix        │
│                                                             │
│  Round 3:                                                   │
│    Generator → Final Solution C (addresses all feedback)    │
│    Critic    → ACCEPTS ✅                                   │
│    Validator → Checks real-world feasibility ✅             │
│                                                             │
│  Output: Refined, validated, consensus-approved solution    │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ TIER 3: IMPLEMENTATION                                      │
│ Code Generator → Validator → Optimizer                      │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ TIER 4: PUBLISHING                                          │
│ Repo Scaffolder → Docs → GitHub Publisher                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 EXAMPLE: CRITIC-GENERATOR DEBATE

### Scenario: Improving Image Classification

**Round 1:**

**Generator:**
```
Proposed Solution: "Multi-Scale Vision Transformer"
- Use Vision Transformer with 3 parallel branches
- Each branch processes different resolutions
- Fuse features with attention mechanism
Expected: +2% accuracy on ImageNet
```

**Critic:**
```
CRITIQUE:
Strengths:
  ✅ Multi-scale processing is sound
  ✅ ViT is well-established

Weaknesses:
  ❌ 3 parallel branches = 3x compute cost!
  ❌ Attention fusion adds more overhead
  ❌ +2% accuracy not worth 3x cost
  ❌ No mention of inference time
  ❌ Missing: How to handle different aspect ratios?

Verdict: REVISE
Suggestions:
  - Use progressive downsampling instead of parallel branches
  - Share weights across scales
  - Add early exit mechanism for efficiency
```

**Round 2:**

**Generator:**
```
REVISED Solution: "Efficient Progressive Multi-Scale ViT"
- Single backbone with progressive downsampling
- Shared weights across scales (parameter efficient!)
- Early exit after each scale if confidence high
- Adaptive resolution based on input complexity
Expected: +1.8% accuracy, only 1.3x compute cost
```

**Critic:**
```
CRITIQUE:
Strengths:
  ✅ Much more efficient! 1.3x vs 3x
  ✅ Early exit is clever
  ✅ Adaptive resolution addresses my concern
  ✅ Shared weights = good generalization

Minor Concerns:
  ⚠️ Early exit might hurt accuracy on hard samples
  ⚠️ Need careful threshold tuning for confidence

Verdict: ACCEPT with minor notes
Recommendation: Add ablation study for early exit threshold
```

**Real-World Validator:**
```
VALIDATION:
✅ GPU Memory: 8GB (fits on RTX 3090)
✅ Training Time: ~24 hours (reasonable)
✅ Inference: 45ms per image (acceptable)
✅ Dataset: ImageNet publicly available
✅ Dependencies: pytorch, timm (standard)
⚠️ Warning: Early exit needs calibration dataset

Overall: FEASIBLE - Proceed to implementation
```

---

## 🛡️ ERROR RECOVERY EXAMPLES

### Example 1: Ollama Connection Lost

```python
# Supervisor detects Ollama down
[07:30:15] ERROR    Ollama connection failed after 3 retries
[07:30:15] WARNING  Entering PAUSED state
[07:30:15] INFO     Checkpoint saved to: state_checkpoint_073015.json
[07:30:15] INFO     Waiting for Ollama to recover...
[07:30:45] INFO     Ollama back online ✅
[07:30:45] INFO     Resuming from checkpoint...
[07:30:46] INFO     Pipeline RUNNING - continuing from Agent 2.5.2 (Critic)
```

### Example 2: Max Errors Reached

```python
[08:15:30] ERROR    Agent failed: novelty_classifier (JSON parsing)
[08:15:32] ERROR    Agent failed: novelty_classifier (JSON parsing)
[08:15:34] ERROR    Agent failed: novelty_classifier (JSON parsing)
[08:15:36] ERROR    Agent failed: novelty_classifier (JSON parsing)
[08:15:38] ERROR    Agent failed: novelty_classifier (JSON parsing)
[08:15:38] CRITICAL 🛑 CIRCUIT BREAKER ACTIVATED
[08:15:38] ERROR    5 consecutive failures detected
[08:15:38] INFO     Error report saved: error_report_081538.json
[08:15:38] INFO     Pipeline HALTED - manual intervention required
[08:15:38] INFO     To resume: python run.py resume --checkpoint state_checkpoint_081530.json
```

### Example 3: Graceful Shutdown (Ctrl+C)

```python
[09:00:00] INFO     Processing paper 5/20...
^C
[09:00:01] WARNING  Interrupt signal received (Ctrl+C)
[09:00:01] INFO     Initiating graceful shutdown...
[09:00:01] INFO     Saving checkpoint...
[09:00:02] INFO     Checkpoint saved: state_checkpoint_090002.json
[09:00:02] INFO     Cleaning up resources...
[09:00:02] INFO     Closing ChromaDB connection
[09:00:02] INFO     Closing Ollama client
[09:00:03] INFO     ✅ Shutdown complete
[09:00:03] INFO     To resume: python run.py resume --checkpoint state_checkpoint_090002.json
```

---

## 📁 FILE STRUCTURE FOR NEW COMPONENTS

```
src/
├── agents/
│   ├── tier0_supervisor/
│   │   ├── supervisor.py              # Main orchestrator
│   │   ├── health_monitor.py          # System health checks
│   │   ├── error_handler.py           # Error recovery logic
│   │   ├── state_manager.py           # Checkpoint management
│   │   └── circuit_breaker.py         # Failure detection
│   │
│   ├── tier2_debate/
│   │   ├── solution_generator.py      # Proposes solutions
│   │   ├── expert_critic.py           # Reviews and critiques
│   │   ├── debate_moderator.py        # Orchestrates rounds
│   │   └── realworld_validator.py     # Feasibility checks
│   │
│   └── tier2_problem/
│       └── problem_extractor.py       # Extract problem statements
│
├── pipeline/
│   ├── state.py                       # State definitions
│   ├── graph.py                       # LangGraph pipeline
│   └── checkpointing.py               # Checkpoint utilities
│
└── utils/
    ├── ollama_client.py               # Ollama interface
    ├── error_types.py                 # Custom exceptions
    └── metrics.py                     # Performance tracking
```

---

## 🎯 IMPLEMENTATION PRIORITY

### Phase 1: Supervisor (Critical!)
```bash
Priority: HIGHEST
ETA: 4-6 hours

Tasks:
1. Create supervisor.py with state machine
2. Add health monitoring for Ollama
3. Implement checkpoint save/load
4. Add graceful shutdown handling
5. Test error recovery scenarios
```

### Phase 2: Critic-Generator Debate
```bash
Priority: HIGH
ETA: 6-8 hours

Tasks:
1. Create solution_generator.py
2. Create expert_critic.py
3. Create debate_moderator.py
4. Add real-world validator
5. Test multi-round debate
```

### Phase 3: Integration
```bash
Priority: MEDIUM
ETA: 3-4 hours

Tasks:
1. Integrate supervisor into run.py
2. Add debate system to pipeline graph
3. Update state definitions
4. Add new CLI commands (resume, status)
```

---

## 🚀 BENEFITS OF THIS ARCHITECTURE

### 1. Self-Improvement
- Solutions get refined through debate
- Multiple perspectives considered
- Flaws caught before implementation

### 2. Fault Tolerance
- Graceful error handling
- Automatic recovery
- No lost work

### 3. Production-Ready
- Real-world validation
- Resource monitoring
- Checkpointing

### 4. Transparency
- Full debate history saved
- Decision reasoning tracked
- Reproducible results

### 5. Quality Assurance
- Expert review of every solution
- Multiple validation layers
- Consensus-based approval

---

## 🎓 RESEARCH INSPIRATION

This architecture is inspired by:
1. **Constitutional AI** (Anthropic) - Self-critique
2. **AutoGPT** - Multi-agent systems
3. **LangGraph** - Stateful workflows
4. **Kubernetes** - Supervisor pattern
5. **Circuit Breaker Pattern** - Fault tolerance

---

## ✅ NEXT STEPS

1. **Start with Supervisor** (most critical for stability)
2. **Add Critic-Generator Debate** (improves solution quality)
3. **Test end-to-end** with real papers
4. **Iterate and refine** based on results

This will transform the system from a "paper processor" to a **"intelligent research assistant"** that:
- Thinks critically
- Refines ideas iteratively
- Handles failures gracefully
- Produces high-quality results

Let's build it! 🚀
