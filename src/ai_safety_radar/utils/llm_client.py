import instructor
from litellm import acompletion
from pydantic import BaseModel
from typing import TypeVar, Type, cast
import logging
from ..config import settings

T = TypeVar('T', bound=BaseModel)
logger = logging.getLogger(__name__)

class LLMClient:
    """Wrapper around LiteLLM + Instructor for structured extraction."""
    
    def __init__(self) -> None:
        self.client = instructor.from_litellm(acompletion)
    
    async def extract(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: str | None = None,
        temperature: float = 0.1
    ) -> T:
        """
        Extract structured data from text using LLM.
        
        Args:
            prompt: User prompt text
            response_model: Pydantic model to extract
            system_prompt: Optional system instructions
            temperature: Sampling temperature
            
        Returns:
            Instance of response_model with extracted data
            
        Raises:
            Exception: If extraction fails (LiteLLM or Instructor errors)
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        

        # For OpenAI, litellm handles it without prefix usually, but let's be safe or rely on settings. 
        # Actually, LiteLLM format is provider/model for some, or just model for OpenAI.
        # settings.llm_model defaults to "gpt-4o-mini"
        
        model_name = settings.llm_model
        if settings.llm_provider == "ollama":
            model_name = f"ollama/{settings.llm_model}" # Correct LiteLLM syntax for Ollama
            
        try:
            timestamp_str = " (Local)" if settings.llm_provider == "ollama" else ""
            logger.info(f"Calling LLM{timestamp_str}: {model_name}")
            
            kwargs = {
                "model": model_name,
                "messages": messages,
                "response_model": response_model,
                "temperature": temperature,
            }
            
            if settings.llm_provider == "ollama":
                kwargs["api_base"] = settings.ollama_base_url

            resp = await self.client.chat.completions.create(**kwargs)
            return cast(T, resp)
            
        except Exception as e:
            logger.error(f"LLM Extraction failed: {e}")
            raise
