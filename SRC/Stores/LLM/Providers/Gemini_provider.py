from ..LLMInterface import LLMInterface
from ..LLMEnums import LLMEnums, GeminiEnum
from google import genai
from google.genai import types
import logging
import os
import time
from typing import List, Union


class GeminiProvider(LLMInterface):
    def __init__(self, api_key: str,
                 api_version: str = "v1",
                 default_input_max_characters: int = 1000,
                 default_genrated_max_output_tokens: int = 8192,
                 default_genration_temperature: float = 0.2):

        self.api_key = api_key
        self.api_version = api_version or "v1"
        self.default_input_max_characters = default_input_max_characters
        self.default_genrated_max_output_tokens = default_genrated_max_output_tokens
        self.default_genration_temperature = default_genration_temperature

        self.genration_model_id = None
        self.embedding_model_id = None
        self.embedding_size = None

        if self.api_key:
            http_options = types.HttpOptions(api_version=self.api_version)
            self.client = genai.Client(api_key=self.api_key, http_options=http_options)
        else:
            self.client = None
            
        self.enums = GeminiEnum
        self.logger = logging.getLogger('uvicorn')

    def set_genration_model(self, model_id: str):
        self.genration_model_id = model_id

    def set_embedding_model(self, model_id: str, embedding_size: int):
        if model_id and not model_id.startswith("models/"):
            model_id = f"models/{model_id}"
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size

    def process_text(self, text: str):
        # Removed truncation as requested
        return text.strip()

    def genrate_text(self, prompt: str, max_output_tokens: int = None, temperature: float = None,
                     chat_history: list = [], max_prompt_characters: int = None):
        if not self.client:
            self.logger.error("Gemini client is not initialized")
            return None

        if not self.genration_model_id:
            self.logger.error("Gemini generation model is not initialized")
            return None

        max_output_tokens = max_output_tokens if max_output_tokens else self.default_genrated_max_output_tokens
        temperature = temperature if temperature else self.default_genration_temperature

        # Convert chat history to Gemini format and extract system instruction
        gemini_history = []
        system_instruction = None

        for message in chat_history:
            role = message.get("role")
            content = message.get("content")
            
            if role == GeminiEnum.SYSTEM.value:
                system_instruction = content
            elif role == GeminiEnum.USER.value:
                gemini_history.append(types.Content(role="user", parts=[types.Part(text=content)]))
            elif role == GeminiEnum.ASSISTANT.value:
                gemini_history.append(types.Content(role="model", parts=[types.Part(text=content)]))

        # Append the current prompt (do not truncate when max_prompt_characters set, e.g. for RAG)
        prompt_text = (prompt[:max_prompt_characters].strip() if max_prompt_characters is not None
                       else self.process_text(prompt))
        gemini_history.append(types.Content(role="user", parts=[types.Part(text=prompt_text)]))

        generation_config = types.GenerateContentConfig(
            max_output_tokens=max_output_tokens,
            temperature=temperature,
            system_instruction=system_instruction
        )
        
        retries = 3
        for attempt in range(retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.genration_model_id,
                    contents=gemini_history,
                    config=generation_config
                )
                
                if not response or not response.text:
                    if attempt < retries:
                        self.logger.error("Error while generating text using Gemini: Empty response")
                        return None
                    return None
                    
                return response.text
                
            except Exception as e:
                is_rate_limit = "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "503" in str(e) or "UNAVAILABLE" in str(e)
                if is_rate_limit:
                    if attempt < retries:
                        wait_time = 4 * (2 ** attempt) # 4, 8, 16 
                        self.logger.warning(f"Gemini rate limit hit. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        self.logger.error(f"Gemini rate limit exhausted after {retries} retries: {e}")
                else:
                    self.logger.error(f"Error calling Gemini API: {e}")
                
                return None

    def embed_text(self, text: Union[str,List[str]], document_type: str = None):
        if not self.client:
            self.logger.error("Gemini client is not initialized")
            return None

        if isinstance(text, str) :
            text = [text]

        if not self.embedding_model_id:
            self.logger.error("Gemini embedding model is not initialized")
            return None

        retries = 3
        for attempt in range(retries + 1):
            try:
                # Gemini embedding task type
                task_type = "RETRIEVAL_DOCUMENT" if document_type == "document" else "RETRIEVAL_QUERY"
                
                result = self.client.models.embed_content(
                    model=self.embedding_model_id,
                    contents=text,
                    config=types.EmbedContentConfig(
                        task_type=task_type,
                        title="Embedding" if task_type == "RETRIEVAL_DOCUMENT" else None 
                    )
                )
                
                if not result or not result.embeddings:
                    self.logger.error("Error while embedding text using Gemini")
                    return None
                return [res.values for res in result.embeddings ]
                
                
            except Exception as e:
                is_rate_limit = "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "503" in str(e) or "UNAVAILABLE" in str(e)
                if is_rate_limit:
                    if attempt < retries:
                        wait_time = 4 * (2 ** attempt) # 4, 8, 16
                        self.logger.warning(f"Gemini rate limit hit (Embedding). Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        self.logger.error(f"Gemini embedding rate limit exhausted after {retries} retries: {e}")
                else:
                    self.logger.error(f"Error calling Gemini Embedding API: {e}")
                
                return None

    def construct_prompt(self, prompt: str, role: str):
        # This is used by the controller to append to history. 
        return {"role": role, "content": prompt}
