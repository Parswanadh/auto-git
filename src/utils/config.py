"""
Configuration management for AUTO-GIT Publisher.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field


class Config(BaseModel):
    """Global configuration."""
    
    # API Keys
    groq_api_key: str
    github_token: str
    github_username: str
    
    # Models
    primary_code_model: str = "openai/gpt-oss-120b"
    analysis_model: str = "openai/gpt-oss-20b"
    local_code_model: str = "deepseek-coder-v2:16b"
    local_analysis_model: str = "deepcoder:14b"
    embedding_model: str = "all-minilm:latest"
    
    # Thresholds
    novelty_threshold: float = 7.0
    priority_threshold: float = 0.5
    complexity_review_threshold: float = 8.0
    
    # Pipeline
    max_papers_per_run: int = 5
    dry_run: bool = True
    human_review_enabled: bool = True
    debug: bool = False
    
    # Rate Limits
    groq_120b_rpm: int = 30
    groq_20b_rpm: int = 30
    max_retries: int = 3
    retry_delay_seconds: int = 2
    
    # Paths
    db_path: str = "./data/pipeline.db"
    vector_db_path: str = "./data/vector_db"
    cache_path: str = "./data/cache"
    log_dir: str = "./logs"
    
    # Logging
    log_level: str = "INFO"
    
    # Cost Controls
    daily_spending_limit: float = 10.0
    spending_alert_threshold: float = 8.0
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML and environment variables.
    
    Args:
        config_path: Path to config.yaml (default: ./config.yaml)
    
    Returns:
        Merged configuration dictionary
    """
    # Load environment variables
    load_dotenv()
    
    # Load YAML config
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config.yaml"
    
    with open(config_path, 'r', encoding='utf-8') as f:
        yaml_config = yaml.safe_load(f)
    
    # Merge with environment variables (env vars take precedence)
    config = yaml_config.copy()
    
    # Override with environment variables
    env_overrides = {
        'groq_api_key': os.getenv('GROQ_API_KEY'),
        'github_token': os.getenv('GITHUB_TOKEN'),
        'github_username': os.getenv('GITHUB_USERNAME'),
        'primary_code_model': os.getenv('PRIMARY_CODE_MODEL'),
        'analysis_model': os.getenv('ANALYSIS_MODEL'),
        'local_code_model': os.getenv('LOCAL_CODE_MODEL'),
        'local_analysis_model': os.getenv('LOCAL_ANALYSIS_MODEL'),
        'embedding_model': os.getenv('EMBEDDING_MODEL'),
        'novelty_threshold': float(os.getenv('NOVELTY_THRESHOLD', '7.0')),
        'priority_threshold': float(os.getenv('PRIORITY_THRESHOLD', '0.5')),
        'max_papers_per_run': int(os.getenv('MAX_PAPERS_PER_RUN', '5')),
        'dry_run': os.getenv('DRY_RUN', 'true').lower() == 'true',
        'log_level': os.getenv('LOG_LEVEL', 'INFO'),
        'debug': os.getenv('DEBUG', 'false').lower() == 'true',
    }
    
    # Remove None values
    env_overrides = {k: v for k, v in env_overrides.items() if v is not None}
    
    # Update config with env overrides
    if 'pipeline' not in config:
        config['pipeline'] = {}
    config['pipeline'].update(env_overrides)
    
    return config


def get_config() -> Config:
    """
    Get validated configuration object.
    
    Returns:
        Config object with all settings
    """
    load_dotenv()
    
    return Config(
        groq_api_key=os.getenv('GROQ_API_KEY', ''),
        github_token=os.getenv('GITHUB_TOKEN', ''),
        github_username=os.getenv('GITHUB_USERNAME', ''),
        primary_code_model=os.getenv('PRIMARY_CODE_MODEL', 'openai/gpt-oss-120b'),
        analysis_model=os.getenv('ANALYSIS_MODEL', 'openai/gpt-oss-20b'),
        local_code_model=os.getenv('LOCAL_CODE_MODEL', 'deepseek-coder-v2:16b'),
        local_analysis_model=os.getenv('LOCAL_ANALYSIS_MODEL', 'deepcoder:14b'),
        embedding_model=os.getenv('EMBEDDING_MODEL', 'all-minilm:latest'),
        novelty_threshold=float(os.getenv('NOVELTY_THRESHOLD', '7.0')),
        priority_threshold=float(os.getenv('PRIORITY_THRESHOLD', '0.5')),
        max_papers_per_run=int(os.getenv('MAX_PAPERS_PER_RUN', '5')),
        dry_run=os.getenv('DRY_RUN', 'true').lower() == 'true',
        human_review_enabled=os.getenv('HUMAN_REVIEW_ENABLED', 'true').lower() == 'true',
        debug=os.getenv('DEBUG', 'false').lower() == 'true',
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
    )
