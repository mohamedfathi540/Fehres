from ..LLMInterface import LLMInterface
from ..LLMEnums import OllamaEnum, DocumentTypeEnum
from langchain_ollama import ChatOllama, OllamaEmbeddings
from ollama import Client as OllamaClient
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
import logging
from typing import List, Union


class OllamaProvider(LLMInterface):
    def __init__(self, base_url: str = None,
                 default_input_max_characters: int = 1000,
                 default_genrated_max_output_tokens: int = 1000,
                 default_genration_temperature: float = 0.1):
        self.base_url = base_url
        self.default_input_max_characters = default_input_max_characters
        self.default_genrated_max_output_tokens = default_genrated_max_output_tokens
        self.default_genration_temperature = default_genration_temperature

        self.genration_model_id = None
        self.embedding_model_id = None
        self.embedding_size = None

        self.enums = OllamaEnum
        self.logger = logging.getLogger(__name__)

    def set_genration_model(self, model_id: str):
        self.genration_model_id = model_id

    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size

    def process_text(self, text: str):
        return text[:self.default_input_max_characters].strip()

    def _build_messages(self, chat_history: list, prompt: str, max_prompt_characters: int = None):
        messages = []
        for message in chat_history:
            role = message.get("role")
            content = message.get("content")
            if role == self.enums.SYSTEM.value:
                messages.append(SystemMessage(content=content))
            elif role == self.enums.USER.value:
                messages.append(HumanMessage(content=content))
            elif role == self.enums.ASSISTANT.value:
                messages.append(AIMessage(content=content))
        # RAG sends a long prompt (many docs); do not truncate when max_prompt_characters is set
        if max_prompt_characters is not None:
            content = prompt[:max_prompt_characters].strip() if prompt else ""
        else:
            content = self.process_text(prompt)
        messages.append(HumanMessage(content=content))
        return messages

    def genrate_text(self, prompt: str, max_output_tokens: int = None,
                     temperature: float = None, chat_history: list = [],
                     max_prompt_characters: int = None):
        if not self.genration_model_id:
            self.logger.error("Ollama generation model is not initialized")
            return None

        max_output_tokens = max_output_tokens if max_output_tokens else self.default_genrated_max_output_tokens
        temperature = temperature if temperature else self.default_genration_temperature

        try:
            client = ChatOllama(
                model=self.genration_model_id,
                base_url=self.base_url,
                temperature=temperature,
                num_predict=max_output_tokens
            )
            messages = self._build_messages(chat_history, prompt, max_prompt_characters)
            response = client.invoke(messages)
            if not response or not getattr(response, "content", None):
                self.logger.error("Error while generating text using Ollama")
                return None
            return response.content
        except Exception as e:
            self.logger.error(f"Exception during Ollama generation: {e}")
            return None

    def embed_text(self, text: Union[str, List[str]], document_type: str = None):
        if not self.embedding_model_id:
            self.logger.error("Ollama embedding model is not initialized")
            return None

        if isinstance(text, str):
            text = [text]

        try:
            processed = [self.process_text(t) for t in text]
            client = OllamaClient(host=self.base_url)
            response = client.embed(
                model=self.embedding_model_id,
                input=processed,
                dimensions=self.embedding_size,
            )
            embeddings = response.embeddings

            if document_type == DocumentTypeEnum.QUERY.value and len(embeddings) == 1:
                return [embeddings[0]]

            return embeddings
        except Exception as e:
            self.logger.error(f"Exception during Ollama embedding: {e}")
            return None

    def construct_prompt(self, prompt: str, role: str):
        return {"role": role, "content": prompt}
