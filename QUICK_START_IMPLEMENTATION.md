# 🎯 QUICK START GUIDE: Cloud API Integration

## 🚀 IMMEDIATE ACTION PLAN

### What You're Building
Add cloud API support (GPT-4, Claude, GLM-4.5) to an existing local LLM agentic system while keeping everything backward compatible.

### Current System
- **Framework**: LangGraph + LangChain + Ollama
- **Models**: Local only (deepseek-coder-v2:16b, qwen3:4b, etc.)
- **Pipeline**: 4-tier agent system for research → analysis → code gen → publishing

### Target System
- **Framework**: Same (LangGraph + LangChain)
- **Models**: Local OR Online OR Hybrid (user choice)
- **Pipeline**: Same, but LLMs are swappable

---

## 📋 STEP-BY-STEP IMPLEMENTATION

### STEP 1: Create Provider Abstraction (Day 1-2)

#### File 1: `src/utils/llm_providers/base_provider.py`
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, AsyncIterator

class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers"""
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate completion"""
        pass
    
    @abstractmethod
    async def stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """Stream completion"""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get model metadata"""
        pass
    
    @abstractmethod
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate API cost"""
        pass
```

#### File 2: `src/utils/llm_providers/ollama_provider.py`
```python
from .base_provider import BaseLLMProvider
from ollama import AsyncClient
import logging

logger = logging.getLogger(__name__)

class OllamaProvider(BaseLLMProvider):
    """Local Ollama provider (existing functionality)"""
    
    def __init__(self, model: str, base_url: str = "http://localhost:11434"):
        self.model = model
        self.client = AsyncClient(host=base_url, timeout=120)
    
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        options = {"temperature": temperature}
        if max_tokens:
            options["num_predict"] = max_tokens
        
        response = await self.client.generate(
            model=self.model,
            prompt=prompt,
            system=system,
            options=options
        )
        
        return {
            "content": response.get("response", ""),
            "model": self.model,
            "usage": {
                "prompt_tokens": response.get("prompt_eval_count", 0),
                "completion_tokens": response.get("eval_count", 0),
            }
        }
    
    async def stream(self, prompt: str, **kwargs):
        async for chunk in self.client.generate(
            model=self.model,
            prompt=prompt,
            stream=True
        ):
            yield chunk.get("response", "")
    
    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "ollama",
            "model": self.model,
            "cost_per_token": 0.0,  # Local = free!
        }
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return 0.0  # Local models are free
```

#### File 3: `src/utils/llm_providers/openai_provider.py`
```python
from .base_provider import BaseLLMProvider
from openai import AsyncOpenAI
import logging

logger = logging.getLogger(__name__)

class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider"""
    
    # Pricing (per 1M tokens, as of Dec 2025)
    PRICING = {
        "gpt-4-turbo": {"input": 10.0, "output": 30.0},
        "gpt-4": {"input": 30.0, "output": 60.0},
        "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
    }
    
    def __init__(self, model: str, api_key: str):
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key)
    
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        return {
            "content": response.choices[0].message.content,
            "model": self.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
            }
        }
    
    async def stream(self, prompt: str, **kwargs):
        messages = [{"role": "user", "content": prompt}]
        
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            **kwargs
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "openai",
            "model": self.model,
            "pricing": self.PRICING.get(self.model, {}),
        }
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        pricing = self.PRICING.get(self.model, {"input": 0, "output": 0})
        cost = (input_tokens / 1_000_000 * pricing["input"]) + \
               (output_tokens / 1_000_000 * pricing["output"])
        return cost
```

#### File 4: `src/utils/llm_factory.py`
```python
from typing import Dict, Any, Optional
from .llm_providers.base_provider import BaseLLMProvider
from .llm_providers.ollama_provider import OllamaProvider
from .llm_providers.openai_provider import OpenAIProvider
# Import other providers as needed
import logging

logger = logging.getLogger(__name__)

class LLMFactory:
    """Factory for creating LLM providers based on configuration"""
    
    _config: Optional[Dict[str, Any]] = None
    _providers: Dict[str, BaseLLMProvider] = {}
    
    @classmethod
    def initialize(cls, config: Dict[str, Any]):
        """Initialize factory with configuration"""
        cls._config = config
        logger.info(f"LLMFactory initialized in {config.get('llm', {}).get('mode', 'local')} mode")
    
    @classmethod
    def get_provider(cls, task_type: str) -> BaseLLMProvider:
        """
        Get LLM provider for a specific task
        
        Args:
            task_type: "code_generation" | "analysis" | "fast_analysis" | "embedding"
        
        Returns:
            Configured LLM provider
        """
        if not cls._config:
            raise RuntimeError("LLMFactory not initialized. Call initialize() first.")
        
        mode = cls._config.get("llm", {}).get("mode", "local")
        
        # Get model name based on mode and task
        if mode == "local":
            model = cls._config["llm"]["local"].get(task_type)
            provider_key = f"ollama_{model}"
            
            if provider_key not in cls._providers:
                cls._providers[provider_key] = OllamaProvider(model)
            
            return cls._providers[provider_key]
        
        elif mode == "online":
            model = cls._config["llm"]["online"].get(task_type)
            
            # Determine which provider based on model name
            if model.startswith("gpt"):
                provider_key = f"openai_{model}"
                if provider_key not in cls._providers:
                    api_key = cls._config["llm"]["providers"]["openai"]["api_key"]
                    cls._providers[provider_key] = OpenAIProvider(model, api_key)
                return cls._providers[provider_key]
            
            # Add similar logic for other providers (Anthropic, GLM, etc.)
            
        elif mode == "hybrid":
            # Smart selection: expensive tasks → online, cheap tasks → local
            if task_type in ["code_generation"] or "complex" in task_type:
                return cls.get_provider_in_mode("online", task_type)
            else:
                return cls.get_provider_in_mode("local", task_type)
        
        raise ValueError(f"Unknown mode: {mode}")
    
    @classmethod
    def get_provider_in_mode(cls, mode: str, task_type: str) -> BaseLLMProvider:
        """Helper to get provider in specific mode"""
        original_mode = cls._config["llm"]["mode"]
        cls._config["llm"]["mode"] = mode
        provider = cls.get_provider(task_type)
        cls._config["llm"]["mode"] = original_mode
        return provider
```

---

### STEP 2: Update Configuration (Day 2)

#### Update `config.yaml`
Add this section:
```yaml
# ============================================
# LLM CONFIGURATION (Multi-Mode Support)
# ============================================
llm:
  mode: "local"  # Options: "local" | "online" | "hybrid"
  
  # Local models (Ollama)
  local:
    code_generation: "deepseek-coder-v2:16b"
    analysis: "qwen3:4b"
    fast_analysis: "qwen3:4b"
    embedding: "all-minilm"
  
  # Online models (Cloud APIs)
  online:
    code_generation: "gpt-4-turbo"
    analysis: "claude-3-5-sonnet"
    fast_analysis: "gpt-3.5-turbo"
    embedding: "text-embedding-3-small"
  
  # Provider configurations
  providers:
    openai:
      api_key: ${OPENAI_API_KEY}
      base_url: "https://api.openai.com/v1"
      models:
        - "gpt-4-turbo"
        - "gpt-4"
        - "gpt-3.5-turbo"
      
    anthropic:
      api_key: ${ANTHROPIC_API_KEY}
      models:
        - "claude-3-5-sonnet"
        - "claude-3-opus"
    
    glm:
      api_key: ${GLM_API_KEY}
      base_url: "https://open.bigmodel.cn/api/paas/v4"
      models:
        - "glm-4.5"
        - "glm-4"
    
    groq:
      api_key: ${GROQ_API_KEY}
      models:
        - "llama-3.1-70b"
        - "mixtral-8x7b"

# Cost tracking
cost_tracking:
  enabled: true
  daily_limit_usd: 10.0
  alert_threshold_usd: 8.0
```

#### Update `.env.example`
```bash
# Existing
GROQ_API_KEY=your_groq_key
GITHUB_TOKEN=your_github_token
GITHUB_USERNAME=your_username

# NEW: Online LLM API Keys
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GLM_API_KEY=your_glm_key
LLM_MODE=local  # or "online" or "hybrid"
```

---

### STEP 3: Update Agent Nodes (Day 3-4)

#### Pattern: Before
```python
# OLD CODE (in any agent file)
from src.utils.ollama_client import get_ollama_client

client = get_ollama_client()
response = await client.generate(
    model="qwen3:4b",
    prompt="Analyze this...",
    system="You are an expert...",
    temperature=0.7
)
content = response.get("content")
```

#### Pattern: After
```python
# NEW CODE
from src.utils.llm_factory import LLMFactory

provider = LLMFactory.get_provider("analysis")  # Gets right provider based on mode
response = await provider.generate(
    prompt="Analyze this...",
    system="You are an expert...",
    temperature=0.7
)
content = response.get("content")
```

#### Files to Update
Apply this pattern to ALL these files:
1. `src/langraph_pipeline/nodes.py` (multiple nodes)
2. `src/agents/tier1_discovery/novelty_classifier.py`
3. `src/agents/tier1_discovery/priority_router.py`
4. `src/agents/tier2_problem/problem_extractor.py`
5. `src/agents/tier2_debate/solution_generator.py`
6. `src/agents/tier2_debate/expert_critic.py`
7. `src/agents/tier2_debate/realworld_validator.py`

---

### STEP 4: Add Mode Switching (Day 4-5)

#### Update `run.py`
```python
import click
from src.utils.config import load_config
from src.utils.llm_factory import LLMFactory

@click.command()
@click.option('--mode', type=click.Choice(['local', 'online', 'hybrid']), 
              default=None, help='LLM mode')
def main(mode):
    # Load config
    config = load_config()
    
    # Override mode if provided
    if mode:
        config['llm']['mode'] = mode
    
    # Validate API keys for online mode
    if config['llm']['mode'] in ['online', 'hybrid']:
        validate_api_keys(config)
    
    # Initialize LLM factory
    LLMFactory.initialize(config)
    
    # ... rest of your pipeline
```

---

## 🧪 TESTING

### Test 1: Local Mode (Must Work)
```bash
python run.py --mode local
# Should work exactly as before
```

### Test 2: Online Mode
```bash
export OPENAI_API_KEY=your_key
python run.py --mode online
# Should use GPT-4 instead of qwen3:4b
```

### Test 3: Hybrid Mode
```bash
python run.py --mode hybrid
# Should use online for code_generation, local for analysis
```

---

## 📦 NEW DEPENDENCIES

Add to `requirements.txt`:
```txt
# Cloud LLM Providers
openai>=1.0.0
anthropic>=0.8.0
groq>=0.4.0

# For GLM-4.5 (ZhipuAI)
zhipuai>=2.0.0

# Already have (keep)
langchain>=0.3.0
langchain-ollama>=0.2.0
langgraph>=0.2.0
```

Install:
```bash
pip install openai anthropic groq zhipuai
```

---

## ⚠️ CRITICAL RULES

### ✅ DO
1. Keep `OllamaProvider` working exactly as `ollama_client.py` does now
2. Make all changes backward compatible
3. Add tests for each provider
4. Validate API keys before use
5. Handle API errors gracefully (fall back to local)
6. Track costs for online APIs
7. Use same logging patterns as existing code

### ❌ DON'T
1. Break existing local mode functionality
2. Change `AutoGITState` schema
3. Modify LangGraph workflow structure
4. Remove or rename existing config fields
5. Change CLI commands that users rely on
6. Commit API keys to git

---

## 🎯 MINIMAL VIABLE PRODUCT (MVP)

If time is limited, implement ONLY these providers:
1. ✅ `OllamaProvider` (refactor existing)
2. ✅ `OpenAIProvider` (GPT-4)
3. ✅ `AnthropicProvider` (Claude)

Skip for MVP:
- GLM provider (can add later)
- Groq provider (can add later)
- Embedding mode switching (keep local)
- Cost tracking dashboard (just log costs)
- Hybrid smart selection (just use mode from config)

---

## 📈 PROGRESS TRACKING

### Week 1 Checklist
- [ ] Create `base_provider.py`
- [ ] Create `ollama_provider.py` (refactor)
- [ ] Create `openai_provider.py`
- [ ] Create `anthropic_provider.py`
- [ ] Create `llm_factory.py`
- [ ] Update `config.yaml`
- [ ] Update 7 agent files
- [ ] Add CLI `--mode` flag
- [ ] Test local mode (must work!)
- [ ] Test online mode (with OpenAI)
- [ ] Test hybrid mode

---

## 🆘 HELP & RESOURCES

### If Stuck
1. Check existing `ollama_client.py` for patterns
2. Look at `langchain-openai` source code for API usage
3. Read provider API docs (links in main document)
4. Test each provider in isolation before integrating

### Common Issues
- **"API key not found"**: Check `.env` file and environment variables
- **"Provider not initialized"**: Call `LLMFactory.initialize(config)` in `run.py`
- **"Local mode broken"**: OllamaProvider must match ollama_client.py exactly
- **"Rate limit"**: Add retry logic with exponential backoff (use `tenacity`)

---

## 🎉 SUCCESS = 

When you can run:
```bash
# Local mode (existing behavior)
python run.py --mode local

# Online mode (new!)
python run.py --mode online

# Hybrid mode (new!)
python run.py --mode hybrid
```

And the pipeline completes successfully in ALL THREE modes!

---

**Good luck! Start with `base_provider.py` and work your way through. You got this! 🚀**
