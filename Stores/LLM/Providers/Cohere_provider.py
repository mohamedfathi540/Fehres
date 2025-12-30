from ..LLMInterface import LLMInterface
from ..LLMEnums import LLMEnums, CohereEnum
import cohere
import logging

class CohereProvider(LLMInterface):
    def __init__(self, api_key: str,
                 defualt_input_max_characters: int = 1000,
                 defualt_genrated_max_output_tokens: int = 1000,
                 defualt_genration_temperature: float = 0.1):

        self.api_key = api_key
        self.defualt_input_max_characters = defualt_input_max_characters
        self.defualt_genrated_max_output_tokens = defualt_genrated_max_output_tokens
        self.defualt_genration_temperature = defualt_genration_temperature

        self.genration_model_id = None
        self.client = cohere.Client(api_key=self.api_key) 
    

        self.embedding_model_id = None
        self.embedding_size = None

        self.logger = logging.getLogger(__name__)

    def set_genration_model(self, model_id: str):
        self.genration_model_id = model_id

    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size

    def process_text(self, text: str):
        return text[:self.defualt_input_max_characters].strip()

    def genrate_text(self, prompt: str, max_output_tokens: int = None, temperature: float = None, chat_history: list = []):
        if not self.client:
            self.logger.error("Cohere client is not initialized")
            return None

        if not self.genration_model_id:
            self.logger.error("Cohere genration model is not initialized")
            return None

        max_output_tokens = max_output_tokens if max_output_tokens else self.defualt_genrated_max_output_tokens
        temperature = temperature if temperature else self.defualt_genration_temperature

        # Create the current message object
        current_message = self.construct_prompt(prompt=prompt, role=CohereEnum.USER.value)
        
        # Cohere API expects 'message' for the current turn and 'chat_history' for previous turns.
        # chat_history passed here is likely the full list including previous turns.
        # However, the interface seems to imply we append to it. 
        # In OpenAI provider: chat_history.append(current) -> call(messages=chat_history)
        # For Cohere: we need to separate the *current* message from the *history*.
        
        # If chat_history is passed in, we append the new user message to it conceptually, 
        # but for the API call we split it.
        
        # Important: The 'chat_history' argument in this method signature comes from the caller. 
        # If the caller expects us to append to it and return it modified (mutable list), 
        # or if we strictly use it for the API. 
        # OpenAI provider modifies it: chat_history.append(...)
        
        # Let's match behavior: append to the list so formatting is consistent if reused.
        chat_history.append(current_message)

        # For Cohere chat parameter:
        # message: str (the text of the current message)
        # chat_history: list of dicts (previous messages)
        
        history_for_api = chat_history[:-1] # All except the last one
        current_prompt_text = current_message["message"]
        
        try:
            response = self.client.chat(
                model=self.genration_model_id,
                message=self.process_text(current_prompt_text),
                chat_history=chat_history,
                temperature=temperature,
                max_tokens=max_output_tokens
            )
            
            if not response or not response.text:
                self.logger.error("Error while generating text using Cohere")
                return None
                
            return response.text
            
        except Exception as e:
            self.logger.error(f"Exception during Cohere generation: {e}")
            return None

    def embed_text(self, text: str, document_type: str = None):
        if not self.client:
            self.logger.error("Cohere client is not initialized")
            return None

        if not self.embedding_model_id:
            self.logger.error("Cohere embedding model is not initialized")
            return None

        try:
            input_type = CohereEnum.DOCUMENT.value
            # Cohere embed takes a list of texts
            response = self.client.embed(
                texts=[text],
                model=self.embedding_model_id,
                input_type=document_type if document_type else "search_document" 
                # input_type is often required for v3 models, defaulting safe
            )

            if not response or not response.embeddings or len(response.embeddings) == 0:
                self.logger.error("Error while embedding text using Cohere")
                return None

            return response.embeddings[0]
            
        except Exception as e:
            self.logger.error(f"Exception during Cohere embedding: {e}")
            return None

    def construct_prompt(self, prompt: str, role: str):
        # Cohere expects 'role' and 'message' (or 'text' in some contexts, but 'message' is standard for chat history objects)
        return {"role": role, "text": self.process_text(prompt)}
