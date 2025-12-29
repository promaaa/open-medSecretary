#
# Copyright (c) 2024-2025
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""Local AI services for the medical voice assistant.

All services run 100% on-premise with no cloud API calls.
"""

from pipecat.services.ollama.llm import OLLamaLLMService


class MedicalLLMService(OLLamaLLMService):
    """Medical LLM service using local Ollama.
    
    Extends OLLamaLLMService to work with locally hosted medical-focused
    language models like Llama-3-Meditron or Mistral-Small.
    
    Usage:
        llm = MedicalLLMService(
            model="llama3-meditron:8b",
            base_url="http://localhost:11434/v1",
        )
    """

    def __init__(
        self,
        *,
        model: str = "llama3:8b",
        base_url: str = "http://localhost:11434/v1",
        **kwargs,
    ):
        """Initialize the Medical LLM service.

        Args:
            model: The Ollama model to use. Examples:
                - "llama3:8b" (default Llama 3)
                - "mistral-small:latest" (Mistral Small)
                - Custom model loaded in Ollama
            base_url: The base URL for the Ollama API endpoint.
            **kwargs: Additional keyword arguments passed to OLLamaLLMService.
        """
        super().__init__(model=model, base_url=base_url, **kwargs)
