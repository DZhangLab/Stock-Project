"""
Configuration module for reading environment variables and database settings.
"""
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
# Try to load from current directory first, then from parent directory
env_path = os.path.join(os.path.dirname(__file__), '.env')
if not os.path.exists(env_path):
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'python_ingestion', '.env')
load_dotenv(env_path)


# Default scope of symbols for the AI / news / earnings pipeline.
# Keep as a list so the scheduler/refresh pipeline can iterate generically,
# but the effective default remains AAPL-first.
PIPELINE_SYMBOLS: list[str] = ["AAPL"]


@dataclass
class DatabaseConfig:
    """Database configuration dataclass."""
    host: str
    user: str
    password: str
    database: str
    port: int = 3306
    pool_size: int = 5
    pool_reset_session: bool = True
    autocommit: bool = True


@dataclass
class APIConfig:
    """API configuration dataclass."""
    api_key: str
    base_url: str = "https://api.twelvedata.com"
    timeout: int = 30
    max_retries: int = 3


@dataclass
class AlphaVantageConfig:
    """Alpha Vantage API configuration dataclass."""
    api_key: str
    base_url: str = "https://www.alphavantage.co/query"
    timeout: int = 30


@dataclass
class AIConfig:
    """AI provider configuration dataclass."""
    provider: str
    api_key: str
    model: str
    prompt_version: str
    base_url: str = "https://api.openai.com/v1/responses"
    timeout: int = 60


@dataclass
class Config:
    """Main configuration dataclass."""
    database: DatabaseConfig
    api: APIConfig
    alpha_vantage: AlphaVantageConfig
    ai: AIConfig


def load_config() -> Config:
    """
    Load configuration from environment variables.
    
    Returns:
        Config: Configuration object with database and API settings.
    """
    db_config = DatabaseConfig(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "stock"),
        port=int(os.getenv("DB_PORT", "3306")),
        pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
        pool_reset_session=os.getenv("DB_POOL_RESET_SESSION", "true").lower() == "true",
        autocommit=os.getenv("DB_AUTOCOMMIT", "true").lower() == "true"
    )
    
    api_config = APIConfig(
        api_key=os.getenv("TWELVE_DATA_API_KEY", ""),
        base_url=os.getenv("API_BASE_URL", "https://api.twelvedata.com"),
        timeout=int(os.getenv("API_TIMEOUT", "30")),
        max_retries=int(os.getenv("API_MAX_RETRIES", "3"))
    )

    alpha_vantage_config = AlphaVantageConfig(
        api_key=os.getenv("ALPHA_VANTAGE_API_KEY", ""),
        base_url=os.getenv("ALPHA_VANTAGE_BASE_URL", "https://www.alphavantage.co/query"),
        timeout=int(os.getenv("ALPHA_VANTAGE_TIMEOUT", "30"))
    )

    ai_config = AIConfig(
        provider=os.getenv("AI_PROVIDER", "openai").strip().lower() or "openai",
        api_key=os.getenv("OPENAI_API_KEY", ""),
        model=os.getenv("AI_MODEL", "gpt-4.1-mini"),
        prompt_version=os.getenv("AI_PROMPT_VERSION", "news_ai_summary_v1"),
        base_url=os.getenv("OPENAI_RESPONSES_URL", "https://api.openai.com/v1/responses"),
        timeout=int(os.getenv("OPENAI_TIMEOUT", "60"))
    )

    return Config(
        database=db_config,
        api=api_config,
        alpha_vantage=alpha_vantage_config,
        ai=ai_config
    )
