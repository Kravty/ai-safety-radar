import instructor
import openai
from pydantic import BaseModel
from typing import TypeVar, Type, Optional, Literal
import logging
import time
import os
from ..config import settings
from .secrets import get_openai_key

T = TypeVar('T', bound=BaseModel)
logger = logging.getLogger(__name__)

# Track if effective config has been logged this process
_config_logged = False

def log_effective_config():
    """Log effective model configuration once per process startup."""
    global _config_logged
    if _config_logged:
        return
    _config_logged = True
    
    # Determine provider based on filter model
    filter_model = settings.llm_filter_model
    analysis_model = settings.llm_analysis_model
    provider = "openai" if filter_model.startswith("gpt-") else "ollama"
    
    # Log single unambiguous line
    logger.info(
        f"EFFECTIVE_CONFIG effective_filter_model={filter_model} "
        f"effective_analysis_model={analysis_model} provider={provider}"
    )
    
    # Also log config sources for debugging
    env_filter = os.getenv("LLM_FILTER_MODEL")
    env_analysis = os.getenv("LLM_ANALYSIS_MODEL")
    env_model = os.getenv("LLM_MODEL")
    
    sources = []
    if env_filter:
        sources.append(f"LLM_FILTER_MODEL={env_filter}(env)")
    if env_analysis:
        sources.append(f"LLM_ANALYSIS_MODEL={env_analysis}(env)")
    if env_model:
        sources.append(f"LLM_MODEL={env_model}(env-legacy)")
    if not sources:
        sources.append("source=config.yaml")
    
    logger.info(f"CONFIG_SOURCES {' '.join(sources)}")

class LLMClient:
    """Wrapper around OpenAI/Ollama + Instructor for structured extraction."""
    
    def __init__(self, model: Optional[str] = None, base_url: Optional[str] = None, temperature: Optional[float] = None, role: Literal["filter", "analysis"] = "filter") -> None:
        """
        Initialize LLM client.
        
        Args:
            model: Explicit model name (overrides config)
            base_url: Explicit base URL for Ollama
            temperature: Sampling temperature (None = model default)
            role: 'filter' uses llm_filter_model, 'analysis' uses llm_analysis_model
        
        For OpenAI models (gpt-*), automatically loads API key from secrets.
        For Ollama models, uses local base_url.
        """
        # Log effective config once per process
        log_effective_config()
        
        # Select model based on role if not explicitly provided
        if model:
            self.model = model
        elif role == "filter":
            self.model = settings.llm_filter_model
        else:
            self.model = settings.llm_analysis_model
        
        # gpt-5-nano only supports temperature=1.0 (default), don't pass explicit temp
        if self.model.startswith("gpt-5"):
            self.temperature = None  # Use model default
        else:
            self.temperature = temperature if temperature is not None else settings.llm_temperature
            
        self.role = role
        
        # Auto-detect provider based on model name
        if self.model.startswith("gpt-"):
            # OpenAI model - load API key from secrets
            api_key = get_openai_key()
            self.client = instructor.from_openai(
                openai.AsyncOpenAI(api_key=api_key),
                mode=instructor.Mode.TOOLS
            )
            self.base_url = None
            self.provider = "openai"
            logger.info(f"Initialized OpenAI client: model={self.model} role={role}")
        elif self.model.startswith("ollama/") or "/" not in self.model:
            # Local Ollama model
            self.base_url = base_url or settings.ollama_base_url
            self.client = instructor.from_openai(
                openai.AsyncOpenAI(
                    base_url=self.base_url,
                    api_key="ollama"  # Dummy key for Ollama
                ),
                mode=instructor.Mode.JSON
            )
            self.provider = "ollama"
            logger.info(f"Initialized Ollama client: model={self.model} role={role} base_url={self.base_url}")
        else:
            raise ValueError(f"Unsupported model: {self.model}. Use 'gpt-*' or 'ollama/*'")
    
    async def extract(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> T:
        """
        Extract structured data from text using LLM.
        
        Args:
            prompt: User prompt text
            response_model: Pydantic model to extract
            system_prompt: Optional system instructions
            temperature: Sampling temperature (overrides default)
            
        Returns:
            Instance of response_model with extracted data
            
        Raises:
            Exception: If extraction fails
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        request_ts = time.time()
        
        try:
            # Log request initiation
            logger.info(f"LLM_REQUEST provider={self.provider} model={self.model} timestamp={int(request_ts)} response_model={response_model.__name__}")
            
            # Build kwargs - gpt-5 models don't support temperature parameter at all
            kwargs = {
                "model": self.model,
                "messages": messages,
                "response_model": response_model,
            }
            # Only include temperature for non-gpt-5 models
            if not self.model.startswith("gpt-5"):
                temp = temperature if temperature is not None else self.temperature
                if temp is not None:
                    kwargs["temperature"] = temp
            
            resp = await self.client.chat.completions.create(**kwargs)
            
            # Log successful response
            duration_ms = int((time.time() - request_ts) * 1000)
            logger.info(f"LLM_RESPONSE provider={self.provider} model={self.model} status=success duration_ms={duration_ms}")
            
            return resp
        except Exception as e:
            # Log failed response
            duration_ms = int((time.time() - request_ts) * 1000)
            logger.error(f"LLM_RESPONSE provider={self.provider} model={self.model} status=error duration_ms={duration_ms} error={str(e)[:100]}")
            raise
