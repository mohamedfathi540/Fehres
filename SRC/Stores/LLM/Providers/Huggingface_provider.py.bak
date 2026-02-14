from ..LLMInterface import LLMInterface
from ..LLMEnums import LLMEnums, HuggingFaceEnum
from huggingface_hub import InferenceClient
import logging
import time
from typing import List, Union
import numpy as np


class HuggingFaceProvider(LLMInterface):
    def __init__(self, api_key: str,
                 default_input_max_characters: int = 1000,
                 default_genrated_max_output_tokens: int = 1000,
                 default_genration_temperature: float = 0.1):

        self.api_key = api_key
        self.default_input_max_characters = default_input_max_characters
        self.default_genrated_max_output_tokens = default_genrated_max_output_tokens
        self.default_genration_temperature = default_genration_temperature

        self.genration_model_id = None
        self.embedding_model_id = None
        self.embedding_size = None

        if self.api_key:
            self.client = InferenceClient(token=self.api_key)
        else:
            self.client = None

        self.enums = HuggingFaceEnum
        self.logger = logging.getLogger('uvicorn')

    def set_genration_model(self, model_id: str):
        self.genration_model_id = model_id

    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size

    def process_text(self, text: str):
        return text[:self.default_input_max_characters].strip()

    def genrate_text(self, prompt: str, max_output_tokens: int = None, temperature: float = None,
                     chat_history: list = [], max_prompt_characters: int = None):
        if not self.client:
            self.logger.error("HuggingFace client is not initialized")
            return None

        if not self.genration_model_id:
            self.logger.error("HuggingFace generation model is not initialized")
            return None

        max_output_tokens = max_output_tokens if max_output_tokens else self.default_genrated_max_output_tokens
        temperature = temperature if temperature else self.default_genration_temperature

        # Prepare prompt
        final_prompt = (prompt[:max_prompt_characters].strip() if max_prompt_characters is not None
                        else self.process_text(prompt))
        
        # Build messages for chat completion
        messages = list(chat_history)
        messages.append(self.construct_prompt(prompt=final_prompt, role=HuggingFaceEnum.USER.value))

        retries = 3
        for attempt in range(retries + 1):
            try:
                response = self.client.chat_completion(
                    model=self.genration_model_id,
                    messages=messages,
                    max_tokens=max_output_tokens,
                    temperature=temperature
                )

                if not response or not response.choices or len(response.choices) == 0:
                    self.logger.error("Error while generating text using HuggingFace: Empty response")
                    return None

                return response.choices[0].message.content

            except Exception as e:
                is_rate_limit = "429" in str(e) or "rate" in str(e).lower()
                if is_rate_limit:
                    if attempt < retries:
                        wait_time = 4 * (2 ** attempt)  # 4, 8, 16
                        self.logger.warning(f"HuggingFace rate limit hit. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        self.logger.error(f"HuggingFace rate limit exhausted after {retries} retries: {e}")
                else:
                    self.logger.error(f"Error calling HuggingFace API: {e}")

                return None

    def embed_text(self, text: Union[str, List[str]], document_type: str = None):
        if not self.client:
            raise Exception("HuggingFace client is not initialized")

        if isinstance(text, str):
            text = [text]

        if not self.embedding_model_id:
            raise Exception("HuggingFace embedding model is not initialized")

        retries = 3
        for attempt in range(retries + 1):
            try:
                # HuggingFace feature extraction for embeddings
                embeddings = []
                for t in text:
                    result = self.client.feature_extraction(
                        text=t,
                        model=self.embedding_model_id
                    )
                    # Result is typically a list of floats or nested structure
                    if isinstance(result, list):
                        # If nested (e.g., [[...]], take first element to get embedding vector
                        if len(result) > 0 and isinstance(result[0], list):
                            # Average pooling for sequence output
                            embedding = np.mean(result, axis=0).tolist()
                        else:
                            embedding = result
                        embeddings.append(embedding)
                    else:
                        embeddings.append(list(result))

                return embeddings

            except Exception as e:
                is_rate_limit = "429" in str(e) or "rate" in str(e).lower()
                if is_rate_limit:
                    if attempt < retries:
                        wait_time = 4 * (2 ** attempt)  # 4, 8, 16
                        self.logger.warning(f"HuggingFace rate limit hit (Embedding). Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        error_msg = f"HuggingFace embedding rate limit exhausted after {retries} retries: {e}"
                        self.logger.error(error_msg)
                        raise Exception(error_msg)
                else:
                    error_msg = f"Error calling HuggingFace Embedding API: {e}"
                    self.logger.error(error_msg)
                    raise Exception(error_msg)

    def construct_prompt(self, prompt: str, role: str):
        return {"role": role, "content": prompt}
