"""
Custom exception types for error handling in the pipeline.
"""

class PipelineError(Exception):
    """Base exception for all pipeline errors"""
    pass


class OllamaConnectionError(PipelineError):
    """Ollama server connection failed"""
    pass


class TokenLimitExceeded(PipelineError):
    """Token usage exceeded limits"""
    pass


class AgentExecutionError(PipelineError):
    """Agent execution failed"""
    def __init__(self, agent_name: str, message: str, original_error: Exception = None):
        self.agent_name = agent_name
        self.original_error = original_error
        super().__init__(f"Agent '{agent_name}' failed: {message}")


class ValidationError(PipelineError):
    """Validation check failed"""
    pass


class ResourceExhaustedError(PipelineError):
    """System resources exhausted (memory, disk, etc.)"""
    pass


class CircuitBreakerOpen(PipelineError):
    """Circuit breaker activated due to repeated failures"""
    pass


class CheckpointError(PipelineError):
    """Error saving or loading checkpoint"""
    pass


class ConfigurationError(PipelineError):
    """Invalid configuration"""
    pass
