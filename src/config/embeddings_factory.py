from typing import Any
from llama_index.embeddings.openai import OpenAIEmbedding
from src.config.settings import settings

class EmbeddingsFactory:
    
    @staticmethod
    def get_eval_embed_model() -> Any:
        """
        Returns the embedding model.
        """
        provider = settings.embeddings_provider.upper()
        
        if provider == "OPENAI":
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY is not set for embeddings.")
            return OpenAIEmbedding(
                model="text-embedding-3-small",
                api_key=settings.openai_api_key
            )
            
        # Add other providers here (e.g. HuggingFace, Cohere)
        
        else:
            print(f"Warning: Unknown Embeddings provider '{provider}'. Defaulting to OpenAI.")
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY is not set for embeddings.")
            return OpenAIEmbedding(
                model="text-embedding-3-small",
                api_key=settings.openai_api_key
            )