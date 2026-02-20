from typing import Any
from llama_index.llms.openai import OpenAI
# from llama_index.llms.anthropic import Anthropic
# from llama_index.llms.ollama import Ollama
from src.config.settings import settings

class LLMFactory:
    _instance = None

    @staticmethod
    def get_llm() -> Any:
        provider = settings.llm_provider.upper()
        
        if provider == "OPENAI":
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY is not set.")
            return OpenAI(
                model="gpt-3.5-turbo",
                temperature=0,
                api_key=settings.openai_api_key
            )
            
        elif provider == "ANTHROPIC":
            if not settings.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY is not set.")
                
            try:
                from llama_index.llms.anthropic import Anthropic
            except ImportError:
                 raise ImportError("Please install `llama-index-llms-anthropic` to use Anthropic.")
            
            return Anthropic(model="claude-3-opus-20240229")

        elif provider == "OLLAMA":
            try:
                from llama_index.llms.ollama import Ollama
            except ImportError:
                raise ImportError("Please install `llama-index-llms-ollama` to use Ollama.")
            
            return Ollama(model="llama3", request_timeout=60.0)

        else:
            print(f"Warning: Unknown LLM provider '{provider}'. Defaulting to OpenAI.")
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY is not set.")
            return OpenAI(
                model="gpt-3.5-turbo",
                temperature=0,
                api_key=settings.openai_api_key
            )