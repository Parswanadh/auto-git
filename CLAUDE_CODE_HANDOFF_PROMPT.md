# 🚀 AUTO-GIT PUBLISHER: Cloud API Integration & Enhancement Project

## 📋 PROJECT OVERVIEW

**Current State**: Working agentic framework using local Ollama models  
**Objective**: Integrate cloud API models while maintaining local model capabilities + enhance research capabilities + add LangGraph MCP integration  
**Date**: December 29, 2025  
**Priority**: High - Production Enhancement

---

## 🎯 PROJECT GOALS

### 1. **Dual-Mode LLM Architecture** (PRIMARY GOAL)
- **Current**: System uses only local Ollama models (deepseek-coder-v2:16b, qwen3:4b, etc.)
- **Target**: Add "Online Mode" with cloud API models (GLM-4.5, Claude, GPT-4, etc.) while keeping local mode fully functional
- **Key Requirement**: Keep the agentic framework architecture constant; only swap LLM backends

### 2. **Enhanced Research Agent** (SECONDARY GOAL)
- **Current**: Basic DuckDuckGo search with limited iterations
- **Target**: Multi-iteration extensive research agent with:
  - Deep web search capabilities
  - Iterative refinement of research queries
  - Better result synthesis
  - Research quality validation

### 3. **LangGraph MCP Integration** (ENHANCEMENT)
- Add Model Context Protocol (MCP) server support
- Enable easier skill/tool composition
- Create reusable MCP-compatible agents

### 4. **Skill Library System** (ENHANCEMENT)
- Identify and document required skills for agent building
- Create modular skill components
- Enable easy skill addition/modification

---

## 🏗️ CURRENT ARCHITECTURE

### System Components

#### **Technology Stack**
```yaml
Core Framework:
  - LangGraph: StateGraph-based orchestration
  - LangChain: ChatOllama for local models
  - Python 3.8+
  - Pydantic v2 for schemas

Local Models (Ollama):
  - deepseek-coder-v2:16b - Code generation
  - qwen3:4b - Fast analysis (262K context)
  - gemma2:2b - Lightweight supervisor
  - all-minilm - Embeddings (SBERT)

Data Storage:
  - ChromaDB: Vector database for novelty checking
  - SQLite: Pipeline state/checkpoints
  - YAML: Configuration (config.yaml)

Search/Research:
  - DuckDuckGo: Free web search (no API key)
  - arXiv: Research paper search
  - No rate limits or API costs

Code Quality:
  - pytest, mypy, pylint, black, isort
  - Pre-commit hooks
```

#### **4-Tier Agent Pipeline**
```
TIER 0: SUPERVISOR
  └─ supervisor.py - Health monitoring, error recovery, checkpointing

TIER 1: DISCOVERY
  ├─ paper_scout.py - arXiv monitoring
  ├─ novelty_classifier.py - SBERT + Ollama scoring
  └─ priority_router.py - Complexity estimation

TIER 2: ANALYSIS & DEBATE
  ├─ problem_extractor.py - Extract research problems
  ├─ solution_generator.py - Multi-perspective solution proposals
  ├─ expert_critic.py - Solution critique
  ├─ debate_moderator.py - Orchestrate debate rounds
  └─ realworld_validator.py - Feasibility validation

TIER 3: GENERATION
  └─ (Minimal implementation - needs expansion)

TIER 4: PUBLISHING
  └─ (Minimal implementation - needs expansion)
```

#### **LangGraph Workflow**
```python
# File: src/langraph_pipeline/workflow.py
StateGraph Flow:
  1. research_node → DuckDuckGo + arXiv search
  2. problem_extraction_node → Extract problems
  3. solution_generation_node → Propose solutions (3 perspectives)
  4. critique_node → Cross-perspective review
  5. consensus_check_node → Decide continue/select
     └─> LOOP back to (3) if no consensus
  6. solution_selection_node → Pick best solution
  7. code_generation_node → DeepSeek implementation
  8. code_testing_node → Validate code
  9. git_publishing_node → Publish to GitHub

State: AutoGITState (TypedDict)
  - idea, requirements, research_context
  - problems, solutions, critiques, debate_rounds
  - selected_solution, generated_code
  - current_stage, errors
```

#### **Key Files**
```
Configuration:
  - config.yaml (311 lines) - All settings, model configs, thresholds
  - .env - API keys (GROQ_API_KEY, GITHUB_TOKEN, etc.)
  
Core Pipeline:
  - src/langraph_pipeline/workflow.py - StateGraph definition
  - src/langraph_pipeline/state.py - State schemas (AutoGITState)
  - src/langraph_pipeline/nodes.py (1254 lines) - Node implementations
  
Utilities:
  - src/utils/ollama_client.py - Ollama wrapper with retries
  - src/utils/config.py - Config management
  - src/utils/web_search.py - DuckDuckGo + arXiv
  - src/utils/logger.py - Logging setup
  
Models:
  - src/models/schemas.py - Pydantic schemas
  
Entry Points:
  - run.py - Main CLI
  - test_langgraph_pipeline.py - Test pipeline
  - cli_entry.py - CLI interface
```

---

## 🎯 IMPLEMENTATION TASKS

### **TASK 1: Dual-Mode LLM Architecture** ⭐ PRIMARY

#### 1.1 Design API Abstraction Layer
**Goal**: Create a unified interface that works with both local Ollama and cloud APIs

**Requirements**:
- Abstract base class for LLM providers
- Implementations for:
  - OllamaProvider (existing, refactor)
  - OpenAIProvider (GPT-4, etc.)
  - AnthropicProvider (Claude)
  - GLMProvider (GLM-4.5, ZhipuAI)
  - GroqProvider (fast inference)
- Common interface methods:
  ```python
  async def generate(prompt, system, temperature, max_tokens, **kwargs)
  async def stream(...)
  def get_model_info()
  def estimate_cost(tokens)
  ```

**Files to Create/Modify**:
```
NEW: src/utils/llm_providers/
  ├─ __init__.py
  ├─ base_provider.py - Abstract base class
  ├─ ollama_provider.py - Refactored from ollama_client.py
  ├─ openai_provider.py - OpenAI API
  ├─ anthropic_provider.py - Claude API
  ├─ glm_provider.py - ZhipuAI GLM-4.5
  └─ groq_provider.py - Groq API

MODIFY: src/utils/ollama_client.py
  → Refactor to use OllamaProvider

NEW: src/utils/llm_factory.py
  → Factory pattern for provider selection
```

#### 1.2 Configuration Schema Update
**Goal**: Support mode selection and API credentials

**Requirements**:
- Add `mode` field: "local" | "online" | "hybrid"
- Add model mappings for each mode
- Add API key configuration
- Validate credentials on startup

**Files to Modify**:
```
config.yaml:
  Add:
    llm:
      mode: "local"  # or "online" or "hybrid"
      
      # Local models (existing)
      local:
        code_generation: "deepseek-coder-v2:16b"
        analysis: "qwen3:4b"
        embedding: "all-minilm"
      
      # Online models (NEW)
      online:
        code_generation: "gpt-4-turbo"  # or "glm-4.5"
        analysis: "claude-3-5-sonnet"
        embedding: "text-embedding-3-small"
      
      # Provider configs
      providers:
        openai:
          api_key: ${OPENAI_API_KEY}
          base_url: "https://api.openai.com/v1"
          models: ["gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
        
        anthropic:
          api_key: ${ANTHROPIC_API_KEY}
          models: ["claude-3-5-sonnet", "claude-3-opus"]
        
        glm:
          api_key: ${GLM_API_KEY}
          base_url: "https://open.bigmodel.cn/api/paas/v4"
          models: ["glm-4.5", "glm-4"]
        
        groq:
          api_key: ${GROQ_API_KEY}
          models: ["llama-3.1-70b", "mixtral-8x7b"]

src/utils/config.py:
  - Update Config class with new fields
  - Add provider validation
  - Add credential checking
```

#### 1.3 Update All Agent Nodes
**Goal**: Replace direct Ollama calls with provider abstraction

**Requirements**:
- Replace `ChatOllama(...)` with `LLMFactory.get_llm(...)`
- Replace `get_ollama_client()` with `LLMFactory.get_client()`
- Ensure backward compatibility

**Files to Modify**:
```
ALL files using LLMs:
  - src/langraph_pipeline/nodes.py (multiple nodes)
  - src/agents/tier1_discovery/novelty_classifier.py
  - src/agents/tier1_discovery/priority_router.py
  - src/agents/tier2_problem/problem_extractor.py
  - src/agents/tier2_debate/solution_generator.py
  - src/agents/tier2_debate/expert_critic.py
  - src/agents/tier2_debate/realworld_validator.py

Pattern:
  OLD:
    from src.utils.ollama_client import get_ollama_client
    client = get_ollama_client()
    response = await client.generate(model="qwen3:4b", prompt=...)
  
  NEW:
    from src.utils.llm_factory import LLMFactory
    client = LLMFactory.get_client("analysis")  # Gets provider based on config
    response = await client.generate(prompt=...)  # Model auto-selected from config
```

#### 1.4 Add Mode Switching
**Goal**: Allow runtime mode switching via CLI/environment

**Requirements**:
- CLI flag: `--mode local|online|hybrid`
- Environment variable: `LLM_MODE=online`
- Validation of required API keys for selected mode

**Files to Modify**:
```
run.py / cli_entry.py:
  - Add --mode argument
  - Validate mode on startup
  - Show warning if API keys missing

Example:
  python run.py --mode online
  python run.py --mode hybrid  # Uses online for expensive tasks, local for cheap
```

---

### **TASK 2: Enhanced Research Agent** ⭐ SECONDARY

#### 2.1 Multi-Iteration Research System
**Goal**: Replace single-pass DuckDuckGo search with iterative deep research

**Requirements**:
- Initial broad search
- Analyze results and identify gaps
- Generate refined queries
- Iterate N times (configurable)
- Synthesize findings across iterations
- Quality validation

**Files to Create/Modify**:
```
NEW: src/agents/tier1_research/
  ├─ research_coordinator.py - Orchestrates multi-iteration research
  ├─ query_refiner.py - Generates better queries from previous results
  ├─ result_synthesizer.py - Combines findings across iterations
  └─ quality_validator.py - Validates research completeness

MODIFY: src/utils/web_search.py
  - Add search result ranking
  - Add duplicate detection
  - Add relevance scoring

NEW: src/utils/research_tools.py
  - Content extraction from URLs
  - PDF parsing (if needed)
  - Snippet extraction
  - Citation extraction
```

**Algorithm**:
```python
# Pseudocode for research coordinator
async def deep_research(idea: str, max_iterations: int = 3):
    query = generate_initial_query(idea)
    all_results = []
    
    for i in range(max_iterations):
        # Search
        results = await search(query)
        all_results.extend(results)
        
        # Analyze gaps
        gaps = analyze_research_gaps(all_results, idea)
        if not gaps:
            break  # Research complete
        
        # Refine query for next iteration
        query = generate_refined_query(gaps, previous_queries=[query])
    
    # Synthesize
    synthesis = synthesize_findings(all_results)
    quality = validate_research_quality(synthesis)
    
    return {
        "results": all_results,
        "synthesis": synthesis,
        "quality_score": quality,
        "iterations": i + 1
    }
```

#### 2.2 Additional Search Sources
**Goal**: Go beyond DuckDuckGo

**Options to Add**:
- Google Scholar (via serpapi or scholarly library)
- Semantic Scholar API (free, no key for basic use)
- PubMed (for biomedical papers)
- GitHub search (for implementations)
- HuggingFace papers (ML-specific)

**Files to Create**:
```
src/utils/search_providers/
  ├─ __init__.py
  ├─ duckduckgo_search.py (refactored from web_search.py)
  ├─ semantic_scholar_search.py
  ├─ github_search.py
  └─ huggingface_search.py
```

#### 2.3 Update Research Node
**Goal**: Integrate enhanced research into LangGraph pipeline

**Files to Modify**:
```
src/langraph_pipeline/nodes.py:
  - Modify research_node() to use deep_research()
  - Add progress reporting
  - Add research quality checks
```

---

### **TASK 3: LangGraph MCP Integration** ⭐ ENHANCEMENT

#### 3.1 MCP Server Setup
**Goal**: Make agents accessible via Model Context Protocol

**Requirements**:
- Create MCP server for auto-git agents
- Expose key capabilities as MCP tools
- Enable composition with other MCP servers

**Files to Create**:
```
NEW: src/mcp_server/
  ├─ __init__.py
  ├─ server.py - Main MCP server
  ├─ tools.py - Tool definitions
  ├─ handlers.py - Tool handlers
  └─ config.json - MCP server config

Example tools:
  - research_topic(topic: str) → ResearchReport
  - generate_solution(problem: str) → SolutionProposal
  - critique_solution(solution: dict) → Critique
  - generate_code(spec: dict) → CodeArtifact
```

**Reference**:
- MCP SDK: https://github.com/modelcontextprotocol/sdk
- Use the Python SDK

#### 3.2 LangGraph MCP Skills
**Goal**: Create reusable MCP-compatible skills

**Files to Create**:
```
NEW: src/skills/
  ├─ __init__.py
  ├─ research_skill.py - Research capability
  ├─ code_generation_skill.py - Code gen capability
  ├─ critique_skill.py - Critique capability
  └─ validation_skill.py - Validation capability

Each skill:
  - Can run standalone
  - Can be called via MCP
  - Has clear input/output schema
  - Is composable
```

---

### **TASK 4: Skill Library System** ⭐ ENHANCEMENT

#### 4.1 Identify Required Skills
**Goal**: Document all skills needed for agentic framework

**Skills to Document**:
1. **Research Skills**:
   - Web search
   - Paper search
   - Implementation search
   - Result synthesis

2. **Analysis Skills**:
   - Problem extraction
   - Novelty assessment
   - Complexity estimation
   - Feasibility validation

3. **Generation Skills**:
   - Solution brainstorming
   - Architecture design
   - Code generation
   - Documentation generation

4. **Evaluation Skills**:
   - Critique generation
   - Consensus checking
   - Quality validation
   - Testing

5. **Meta Skills**:
   - Prompt engineering
   - Error recovery
   - State management
   - Progress tracking

**Files to Create**:
```
NEW: SKILLS_CATALOG.md
  - Comprehensive skill documentation
  - Input/output schemas
  - Usage examples
  - Dependencies
```

#### 4.2 Create Skill Templates
**Goal**: Make it easy to add new skills

**Files to Create**:
```
NEW: templates/
  ├─ skill_template.py - Base skill class
  ├─ agent_template.py - Base agent class
  └─ node_template.py - LangGraph node template

NEW: docs/
  ├─ SKILL_DEVELOPMENT.md - How to create skills
  └─ AGENT_DEVELOPMENT.md - How to create agents
```

---

## 📊 IMPLEMENTATION PRIORITY

### Phase 1: Foundation (Week 1)
1. ✅ Task 1.1: API Abstraction Layer (3-4 days)
2. ✅ Task 1.2: Configuration Schema (1 day)
3. ✅ Task 1.3: Update Agent Nodes (2-3 days)

### Phase 2: Mode Switching (Week 2)
4. ✅ Task 1.4: Add Mode Switching (1 day)
5. ✅ Test dual-mode operation (2 days)
6. ✅ Documentation (1 day)

### Phase 3: Research Enhancement (Week 3)
7. ✅ Task 2.1: Multi-Iteration Research (3-4 days)
8. ✅ Task 2.2: Additional Search Sources (2 days)
9. ✅ Task 2.3: Update Research Node (1 day)

### Phase 4: MCP & Skills (Week 4)
10. ✅ Task 3.1: MCP Server Setup (3 days)
11. ✅ Task 3.2: LangGraph MCP Skills (2 days)
12. ✅ Task 4.1: Skill Documentation (1 day)
13. ✅ Task 4.2: Skill Templates (1 day)

---

## 🔍 KEY TECHNICAL DECISIONS

### 1. **Provider Selection Strategy**
```python
# Hybrid Mode Logic
def select_provider(task_type: str, complexity: str) -> Provider:
    if mode == "local":
        return OllamaProvider()
    elif mode == "online":
        return get_online_provider(task_type)
    else:  # hybrid
        if complexity == "high" or task_type == "code_generation":
            return get_online_provider(task_type)  # Use powerful cloud model
        else:
            return OllamaProvider()  # Use fast local model
```

### 2. **Cost Tracking**
- Track API usage per provider
- Estimate costs before API calls
- Alert on budget thresholds
- Daily/weekly spending reports

### 3. **Fallback Strategy**
- If online API fails → fall back to local
- If rate limited → queue and retry
- If quality low → try different provider

### 4. **Configuration Precedence**
```
Environment Variables > CLI Arguments > config.yaml > Defaults
```

---

## 🧪 TESTING STRATEGY

### Unit Tests
```python
# Test each provider
tests/test_providers/
  ├─ test_ollama_provider.py
  ├─ test_openai_provider.py
  ├─ test_anthropic_provider.py
  └─ test_glm_provider.py

# Test mode switching
tests/test_mode_switching.py

# Test research system
tests/test_research/
  ├─ test_research_coordinator.py
  ├─ test_query_refiner.py
  └─ test_result_synthesizer.py
```

### Integration Tests
```python
# Test full pipeline in each mode
tests/integration/
  ├─ test_local_mode.py
  ├─ test_online_mode.py
  └─ test_hybrid_mode.py
```

### E2E Tests
```python
# Test complete workflow
tests/e2e/
  ├─ test_pipeline_local.py
  ├─ test_pipeline_online.py
  └─ test_pipeline_hybrid.py
```

---

## 📚 RESOURCES & REFERENCES

### API Documentation
- **OpenAI**: https://platform.openai.com/docs/api-reference
- **Anthropic Claude**: https://docs.anthropic.com/claude/reference
- **ZhipuAI GLM**: https://open.bigmodel.cn/dev/api
- **Groq**: https://console.groq.com/docs/quickstart

### Libraries
- **LangChain Providers**: Use existing LangChain integrations
  - `langchain-openai`
  - `langchain-anthropic`
  - `langchain-groq`
- **MCP SDK**: https://github.com/modelcontextprotocol/python-sdk

### Current System Patterns
- **State Management**: TypedDict + LangGraph StateGraph
- **Error Handling**: tenacity retry decorators + custom exceptions
- **Logging**: Python logging + Rich console output
- **Config**: YAML + Pydantic models + environment variables

---

## ⚠️ IMPORTANT CONSTRAINTS

### Must Maintain
1. ✅ **Backward Compatibility**: Local mode must work exactly as before
2. ✅ **State Schema**: Don't break AutoGITState structure
3. ✅ **LangGraph Flow**: Keep workflow.py graph structure
4. ✅ **CLI Interface**: Existing commands must still work
5. ✅ **Configuration**: config.yaml should be backward compatible

### Must Add
1. ✅ **Provider Abstraction**: Clean interface for all LLM providers
2. ✅ **Mode Selection**: Easy switching between local/online/hybrid
3. ✅ **Cost Tracking**: Monitor and limit API spending
4. ✅ **Error Handling**: Graceful fallbacks for API failures
5. ✅ **Documentation**: Clear docs for new features

### Must NOT Break
1. ❌ Existing local Ollama workflow
2. ❌ State persistence/checkpointing
3. ❌ Supervisor health monitoring
4. ❌ Debate system logic
5. ❌ Vector database integration

---

## 🎯 SUCCESS CRITERIA

### Task 1: Dual-Mode LLM
- [ ] Can run full pipeline in local mode (existing behavior)
- [ ] Can run full pipeline in online mode (new)
- [ ] Can run full pipeline in hybrid mode (new)
- [ ] Mode selection via CLI: `--mode local|online|hybrid`
- [ ] All agents work with any provider
- [ ] Cost tracking works
- [ ] Fallback to local works when online fails

### Task 2: Enhanced Research
- [ ] Multi-iteration research produces better results than single-pass
- [ ] Research quality score > 0.7 on test cases
- [ ] Supports 3+ search sources beyond DuckDuckGo
- [ ] Iterative refinement shows improvement across iterations

### Task 3: MCP Integration
- [ ] MCP server runs and accepts connections
- [ ] Key tools exposed and functional
- [ ] Can compose with other MCP servers
- [ ] Documentation complete

### Task 4: Skill Library
- [ ] SKILLS_CATALOG.md documents all skills
- [ ] Skill templates provided
- [ ] At least 5 skills extracted and reusable
- [ ] Clear development guide

---

## 🚀 GETTING STARTED

### Step 1: Set Up Development Environment
```bash
cd /d/Projects/auto-git
conda activate auto-git  # or create: conda env create -f environment.yml

# Install new dependencies (will be added)
pip install langchain-openai langchain-anthropic langchain-groq
pip install openai anthropic zhipuai-sdk
pip install mcp  # Model Context Protocol SDK
```

### Step 2: Create Feature Branch
```bash
git checkout -b feature/cloud-api-integration
```

### Step 3: Start with Task 1.1
Begin with the API abstraction layer. This is the foundation for everything else.

**First File to Create**: `src/utils/llm_providers/base_provider.py`

---

## 📞 QUESTIONS TO ADDRESS

1. **GLM-4.5 API**: Do we have API credentials? Need to obtain from ZhipuAI
2. **Budget**: What's the daily spending limit for online APIs?
3. **Default Mode**: Should default be "local", "online", or "hybrid"?
4. **Provider Priority**: In hybrid mode, which provider for which tasks?
5. **Embedding Mode**: Keep embeddings local (all-minilm) or move to OpenAI?
6. **GitHub Search**: Do we need GitHub API token for implementation search?
7. **Rate Limits**: What are acceptable rate limits for each provider?
8. **Testing**: Do we need mock API responses for testing, or use real APIs?

---

## 🎓 LEARNING RESOURCES

### For Claude Code to Study
1. Current codebase structure (all files listed above)
2. LangGraph documentation: https://langchain-ai.github.io/langgraph/
3. Provider API docs (links in Resources section)
4. MCP Protocol: https://modelcontextprotocol.io/

### Key Concepts
- **Provider Pattern**: Abstract interface + concrete implementations
- **Factory Pattern**: Dynamic provider selection based on config
- **State Machine**: LangGraph StateGraph orchestration
- **Error Recovery**: Retry logic + fallback mechanisms

---

## 📝 NOTES

- This is a complex, multi-week project
- Start with Task 1 (Dual-Mode LLM) as it's the foundation
- Each task should be a separate PR for easier review
- Write tests as you go, not after
- Update documentation alongside code changes
- Keep backward compatibility at all times

**Good luck! This is an exciting enhancement to an already impressive system.**

---

## 🔗 RELATED DOCUMENTS

- [README.md](README.md) - Project overview
- [ARCHITECTURE_V2.md](ARCHITECTURE_V2.md) - System architecture
- [LANGGRAPH_SETUP.md](LANGGRAPH_SETUP.md) - LangGraph setup guide
- [config.yaml](config.yaml) - Configuration reference
- [STATUS.md](STATUS.md) - Current implementation status

---

**Last Updated**: December 29, 2025  
**Author**: Auto-Git Team  
**For**: Claude Code Implementation
