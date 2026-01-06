"""Secure secret loading for production deployment."""
from pathlib import Path
import os
from typing import Optional


def get_secret(secret_name: str, env_fallback: Optional[str] = None) -> Optional[str]:
    """
    Load secret from Podman/Docker mount or environment variable.
    
    Priority:
    1. /run/secrets/{secret_name} (Podman/Docker secret mount)
    2. Environment variable (dev convenience)
    
    Args:
        secret_name: Name of the secret (e.g., 'openai_api_key')
        env_fallback: Environment variable name to check if secret file not found
        
    Returns:
        Secret value or None if not found
        
    Raises:
        ValueError: If secret not found in either location
    """
    secret_path = Path(f"/run/secrets/{secret_name}")
    if secret_path.exists():
        try:
            return secret_path.read_text().strip()
        except IOError as e:
            raise ValueError(f"Secret file exists but cannot be read: {secret_path}") from e
    
    if env_fallback:
        value = os.getenv(env_fallback)
        if value:
            return value
    
    raise ValueError(
        f"Secret '{secret_name}' not found. "
        f"Expected at {secret_path} or env var {env_fallback}"
    )


def get_openai_key() -> str:
    """Get OpenAI API key from secure storage."""
    return get_secret("openai_api_key", "OPENAI_API_KEY")
