# ✅ IMPLEMENTATION CHECKLIST

## 📋 PHASE 1: DUAL-MODE LLM ARCHITECTURE (MVP - 1 Week)

### Week 1, Day 1-2: Provider Abstraction Layer
- [ ] Create `src/utils/llm_providers/` directory
- [ ] Create `src/utils/llm_providers/__init__.py`
- [ ] Create `src/utils/llm_providers/base_provider.py`
  - [ ] Define BaseLLMProvider abstract class
  - [ ] Define abstract methods: generate(), stream(), get_model_info(), estimate_cost()
  - [ ] Add type hints and docstrings
- [ ] Create `src/utils/llm_providers/ollama_provider.py`
  - [ ] Refactor code from ollama_client.py
  - [ ] Implement all abstract methods
  - [ ] Ensure backward compatibility (must work exactly as before)
  - [ ] Test with qwen3:4b and deepseek-coder-v2:16b
- [ ] Create `src/utils/llm_providers/openai_provider.py`
  - [ ] Implement OpenAI API integration
  - [ ] Add pricing information (GPT-4, GPT-3.5)
  - [ ] Implement cost estimation
  - [ ] Test with gpt-3.5-turbo first (cheaper)
- [ ] Create `src/utils/llm_factory.py`
  - [ ] Implement LLMFactory class
  - [ ] Add initialize(config) method
  - [ ] Add get_provider(task_type) method
  - [ ] Implement mode switching logic (local/online/hybrid)

**Day 1-2 Success Criteria**:
- [ ] Can import and use OllamaProvider standalone
- [ ] Can import and use OpenAIProvider standalone
- [ ] LLMFactory.get_provider() returns correct provider based on config

---

### Week 1, Day 3: Configuration Updates
- [ ] Update `config.yaml`
  - [ ] Add `llm:` section
  - [ ] Add `llm.mode` field (local/online/hybrid)
  - [ ] Add `llm.local` section (existing models)
  - [ ] Add `llm.online` section (cloud models)
  - [ ] Add `llm.providers` section (API configs)
  - [ ] Add `cost_tracking` section
- [ ] Update `.env.example`
  - [ ] Add OPENAI_API_KEY
  - [ ] Add ANTHROPIC_API_KEY
  - [ ] Add GLM_API_KEY
  - [ ] Add LLM_MODE
- [ ] Update `src/utils/config.py`
  - [ ] Add new config fields to Config class
  - [ ] Add provider validation
  - [ ] Add credential checking
  - [ ] Test config loading

**Day 3 Success Criteria**:
- [ ] Config loads successfully with new fields
- [ ] Can set LLM_MODE via environment variable
- [ ] Validates API keys when mode=online

---

### Week 1, Day 4: Update Agent Nodes (Part 1)
- [ ] Update `src/langraph_pipeline/nodes.py`
  - [ ] Import LLMFactory at top
  - [ ] Find all LLM usage (search for "ChatOllama", "ollama_client")
  - [ ] Replace with LLMFactory.get_provider() calls
  - [ ] Test each node individually
- [ ] Update `src/agents/tier1_discovery/novelty_classifier.py`
  - [ ] Replace get_ollama_client() with LLMFactory.get_provider("analysis")
  - [ ] Test novelty scoring still works
- [ ] Update `src/agents/tier1_discovery/priority_router.py`
  - [ ] Replace get_ollama_client() with LLMFactory.get_provider("fast_analysis")
  - [ ] Test priority routing still works

**Day 4 Success Criteria**:
- [ ] nodes.py uses LLMFactory
- [ ] tier1_discovery agents use LLMFactory
- [ ] Local mode still works for these files

---

### Week 1, Day 5: Update Agent Nodes (Part 2)
- [ ] Update `src/agents/tier2_problem/problem_extractor.py`
  - [ ] Replace get_ollama_client() with LLMFactory.get_provider("analysis")
- [ ] Update `src/agents/tier2_debate/solution_generator.py`
  - [ ] Replace get_ollama_client() with LLMFactory.get_provider("analysis")
- [ ] Update `src/agents/tier2_debate/expert_critic.py`
  - [ ] Replace get_ollama_client() with LLMFactory.get_provider("analysis")
- [ ] Update `src/agents/tier2_debate/realworld_validator.py`
  - [ ] Replace get_ollama_client() with LLMFactory.get_provider("analysis")

**Day 5 Success Criteria**:
- [ ] All agent files updated
- [ ] No references to get_ollama_client() remain (except in ollama_provider.py)
- [ ] Local mode works end-to-end

---

### Week 1, Day 6: CLI Mode Switching
- [ ] Update `run.py`
  - [ ] Add --mode argument (local/online/hybrid)
  - [ ] Initialize LLMFactory with config
  - [ ] Validate API keys for online mode
  - [ ] Show mode in startup message
- [ ] Update `cli_entry.py` (if needed)
  - [ ] Add --mode flag
  - [ ] Pass mode to pipeline
- [ ] Test CLI
  - [ ] `python run.py --mode local` (must work)
  - [ ] `python run.py --mode online` (new!)
  - [ ] `python run.py` (default mode from config)

**Day 6 Success Criteria**:
- [ ] CLI --mode flag works
- [ ] Mode selection is visible to user
- [ ] Error messages clear if API keys missing

---

### Week 1, Day 7: Testing & Documentation
- [ ] Write unit tests
  - [ ] tests/test_providers/test_ollama_provider.py
  - [ ] tests/test_providers/test_openai_provider.py
  - [ ] tests/test_llm_factory.py
- [ ] Write integration tests
  - [ ] tests/integration/test_local_mode.py
  - [ ] tests/integration/test_online_mode.py
- [ ] Manual testing
  - [ ] Run full pipeline in local mode
  - [ ] Run full pipeline in online mode
  - [ ] Verify outputs are reasonable
- [ ] Update documentation
  - [ ] Update README.md with mode switching info
  - [ ] Create USER_GUIDE.md for new features
  - [ ] Document API key setup

**Day 7 Success Criteria**:
- [ ] All tests pass
- [ ] Manual testing successful in both modes
- [ ] Documentation updated

---

## ✅ PHASE 1 COMPLETE CHECKLIST

### Functionality
- [ ] Local mode works exactly as before (backward compatible)
- [ ] Online mode works with OpenAI (GPT-4 or GPT-3.5)
- [ ] Can switch modes via CLI flag
- [ ] Can switch modes via config.yaml
- [ ] Can switch modes via environment variable
- [ ] Error messages clear and helpful

### Code Quality
- [ ] No direct imports of ollama_client in agent files
- [ ] Type hints maintained throughout
- [ ] Docstrings added to new code
- [ ] Follows existing code patterns
- [ ] No breaking changes to AutoGITState

### Testing
- [ ] Unit tests written and passing
- [ ] Integration tests written and passing
- [ ] Manual testing completed
- [ ] Tested with and without API keys
- [ ] Tested fallback scenarios

### Documentation
- [ ] README.md updated
- [ ] config.yaml documented
- [ ] .env.example updated
- [ ] User guide created
- [ ] Code comments added

---

## 📋 PHASE 2: ADDITIONAL PROVIDERS & REFINEMENT (Week 2)

### Week 2, Day 1-2: Anthropic Provider
- [ ] Create `src/utils/llm_providers/anthropic_provider.py`
  - [ ] Implement Claude API integration
  - [ ] Add pricing for Claude models
  - [ ] Implement streaming support
  - [ ] Add to factory selection logic
- [ ] Test Anthropic provider
  - [ ] Unit tests
  - [ ] Integration with pipeline
  - [ ] Cost estimation accuracy

### Week 2, Day 3: Hybrid Mode Logic
- [ ] Implement smart provider selection
  - [ ] High complexity tasks → online
  - [ ] Low complexity tasks → local
  - [ ] Code generation → online
  - [ ] Fast analysis → local
- [ ] Add provider selection logging
- [ ] Test hybrid mode thoroughly

### Week 2, Day 4: Cost Tracking
- [ ] Create `src/utils/cost_tracker.py`
  - [ ] Track usage per provider
  - [ ] Log costs to file
  - [ ] Check against daily limits
  - [ ] Alert on threshold exceeded
- [ ] Integrate into LLMFactory
- [ ] Add cost reporting to CLI

### Week 2, Day 5: Comprehensive Testing
- [ ] Write tests for all providers
- [ ] Test hybrid mode logic
- [ ] Test cost tracking
- [ ] Test error scenarios
- [ ] Load testing (if applicable)

### Week 2, Day 6-7: Documentation & Polish
- [ ] Update all documentation
- [ ] Create troubleshooting guide
- [ ] Add code examples
- [ ] Clean up code
- [ ] Code review

---

## 📋 PHASE 3: ENHANCED RESEARCH (Week 3)

### Week 3, Day 1-2: Multi-Iteration Research
- [ ] Create `src/agents/tier1_research/` directory
- [ ] Create `research_coordinator.py`
  - [ ] Implement multi-iteration logic
  - [ ] Add progress tracking
- [ ] Create `query_refiner.py`
  - [ ] Generate refined queries from gaps
- [ ] Create `result_synthesizer.py`
  - [ ] Combine results across iterations

### Week 3, Day 3-4: Additional Search Sources
- [ ] Create `src/utils/search_providers/` directory
- [ ] Add Semantic Scholar search
- [ ] Add GitHub search
- [ ] Add HuggingFace papers search
- [ ] Integrate into research coordinator

### Week 3, Day 5: Update Research Node
- [ ] Modify `research_node()` in nodes.py
- [ ] Use deep_research instead of single-pass
- [ ] Add quality validation
- [ ] Test improved research quality

### Week 3, Day 6-7: Testing & Documentation
- [ ] Write tests for research system
- [ ] Compare quality vs. old system
- [ ] Document research improvements

---

## 📋 PHASE 4: MCP & SKILLS (Week 4)

### Week 4, Day 1-2: MCP Server
- [ ] Create `src/mcp_server/` directory
- [ ] Implement MCP server
- [ ] Expose key agents as tools
- [ ] Test MCP connections

### Week 4, Day 3: Skill Library
- [ ] Create SKILLS_CATALOG.md
- [ ] Document all current skills
- [ ] Create skill templates
- [ ] Write skill development guide

### Week 4, Day 4-5: Final Polish
- [ ] Code cleanup
- [ ] Final testing
- [ ] Documentation review
- [ ] Performance optimization

---

## 🎯 QUICK REFERENCE: FILES TO CREATE

### New Files (Phase 1)
```
src/utils/llm_providers/
  ├─ __init__.py
  ├─ base_provider.py
  ├─ ollama_provider.py
  └─ openai_provider.py

src/utils/
  └─ llm_factory.py

tests/test_providers/
  ├─ test_ollama_provider.py
  └─ test_openai_provider.py

tests/integration/
  ├─ test_local_mode.py
  └─ test_online_mode.py
```

### Files to Modify (Phase 1)
```
config.yaml                                         (add llm section)
.env.example                                        (add API keys)
src/utils/config.py                                 (add config fields)
run.py                                              (add --mode flag)
src/langraph_pipeline/nodes.py                      (use LLMFactory)
src/agents/tier1_discovery/novelty_classifier.py    (use LLMFactory)
src/agents/tier1_discovery/priority_router.py       (use LLMFactory)
src/agents/tier2_problem/problem_extractor.py       (use LLMFactory)
src/agents/tier2_debate/solution_generator.py       (use LLMFactory)
src/agents/tier2_debate/expert_critic.py            (use LLMFactory)
src/agents/tier2_debate/realworld_validator.py      (use LLMFactory)
```

---

## 🚦 PROGRESS TRACKING

### Current Status: ⬜ Not Started

Update this as you go:

```
Phase 1: Dual-Mode LLM Architecture
  ⬜ Provider Abstraction (Day 1-2)
  ⬜ Configuration Updates (Day 3)
  ⬜ Update Agents Part 1 (Day 4)
  ⬜ Update Agents Part 2 (Day 5)
  ⬜ CLI Mode Switching (Day 6)
  ⬜ Testing & Docs (Day 7)

Phase 2: Additional Providers
  ⬜ Anthropic Provider (Day 1-2)
  ⬜ Hybrid Mode Logic (Day 3)
  ⬜ Cost Tracking (Day 4)
  ⬜ Testing (Day 5)
  ⬜ Documentation (Day 6-7)

Phase 3: Enhanced Research
  ⬜ Multi-Iteration Research (Day 1-2)
  ⬜ Additional Search Sources (Day 3-4)
  ⬜ Update Research Node (Day 5)
  ⬜ Testing & Docs (Day 6-7)

Phase 4: MCP & Skills
  ⬜ MCP Server (Day 1-2)
  ⬜ Skill Library (Day 3)
  ⬜ Final Polish (Day 4-5)
```

Legend:
- ⬜ Not started
- 🔄 In progress
- ✅ Complete
- ❌ Blocked

---

## 📝 NOTES & BLOCKERS

Use this section to track issues:

```
Date: 2025-12-29
Issue: [Description]
Resolution: [How it was fixed]

---

Date: 
Issue: 
Resolution: 

```

---

**Last Updated**: December 29, 2025  
**Project**: AUTO-GIT Cloud API Integration  
**Current Phase**: Not Started  
**Next Action**: Begin Phase 1, Day 1-2 (Provider Abstraction)
