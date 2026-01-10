
try:
    from Stores.LLM.Providers.Gemini_provider import GeminiProvider
    from Stores.LLM.LLMEnums import GeminiEnum
    from Stores.LLM.LLMProviderFactory import LLMProviderFactory
    from Stores.LLM.LLMEnums import LLMEnums
    import google.generativeai as genai
    
    print("Imports successful.")
    
    # Mock config
    class Config:
        GEMINI_API_KEY = "dummy_key"
        INPUT_DEFUALT_MAX_CHARACTERS = 100
        GENRATED_DEFUALT_MAX_OUTPUT_TOKENS = 100
        GENRATION_DEFUALT_TEMPERATURE = 0.5
        OPENAI_API_KEY = "dummy"
        OPENAI_BASE_URL = "dummy"
        COHERE_API_KEY = "dummy"

    factory = LLMProviderFactory(Config())
    provider = factory.create(LLMEnums.GEMINI.value)
    
    if isinstance(provider, GeminiProvider):
        print("Factory created GeminiProvider successfully.")
        
    if provider.client:
        print("Gemini client initialized (mock key).")
    else:
        print("Gemini client not initialized (expected if key invalid/empty, but here we passed dummy).")

except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
