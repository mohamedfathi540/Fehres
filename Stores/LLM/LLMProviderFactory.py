from .LLMEnums import LLMEnums
from .Providers import OpenAIProvider , CohereProvider, GeminiProvider


class LLMProviderFactory :
    def __init__(self,config : dict):
        self.config = config

    def create (self , provider : str ) :
        if provider == LLMEnums.OPENAI.value :
            return OpenAIProvider(
                api_key = self.config.OPENAI_API_KEY,
                base_url = self.config.OPENAI_BASE_URL,
                defualt_input_max_characters = self.config.INPUT_DEFUALT_MAX_CHARACTERS,
                defualt_genrated_max_output_tokens = self.config.GENRATED_DEFUALT_MAX_OUTPUT_TOKENS,
                defualt_genration_temperature = self.config.GENRATION_DEFUALT_TEMPERATURE
            )

        if provider == LLMEnums.COHERE.value :
            return CohereProvider(
                api_key = self.config.COHERE_API_KEY,
                defualt_input_max_characters = self.config.INPUT_DEFUALT_MAX_CHARACTERS,
                defualt_genrated_max_output_tokens = self.config.GENRATED_DEFUALT_MAX_OUTPUT_TOKENS,
                defualt_genration_temperature = self.config.GENRATION_DEFUALT_TEMPERATURE   
            )
                
               
        if provider == LLMEnums.GEMINI.value :
            return GeminiProvider(
                api_key = self.config.GEMINI_API_KEY,
                defualt_input_max_characters = self.config.INPUT_DEFUALT_MAX_CHARACTERS,
                defualt_genrated_max_output_tokens = self.config.GENRATED_DEFUALT_MAX_OUTPUT_TOKENS,
                defualt_genration_temperature = self.config.GENRATION_DEFUALT_TEMPERATURE   
            )

        return None