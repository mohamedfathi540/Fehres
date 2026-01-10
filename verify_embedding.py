
import asyncio
import os
from Helpers.Config import get_settings
from Stores.LLM.Providers.Gemini_provider import GeminiProvider

async def verify_embedding():
    print("Loading settings...")
    try:
        settings = get_settings()
        print(f"Loaded settings. Embedding Model: {settings.EMBEDDING_MODEL_ID}, Gen Backend: {settings.GENRATION_BACKEND}")
        
        if settings.EMBEDDING_BACKEND != "GEMINI":
            print("Skipping Gemini verification as backend is not GEMINI")
            return

        api_key = settings.GEMINI_API_KEY
        if not api_key:
            print("Error: GEMINI_API_KEY is missing via settings. Checking env directly...")
            # Fallback check
            pass

        provider = GeminiProvider(
            api_key=api_key,
            defualt_input_max_characters=1000,
            defualt_genrated_max_output_tokens=100,
            defualt_genration_temperature=0.1
        )
        
        provider.set_embedding_model(settings.EMBEDDING_MODEL_ID, settings.EMBEDDING_SIZE)
        
        print(f"Testing embedding with model: {settings.EMBEDDING_MODEL_ID}")
        text = "This is a test sentence to verify embeddings."
        embedding = provider.embed_text(text, document_type="query")
        
        if embedding:
            print(f"Success! Generated embedding of length: {len(embedding)}")
            if len(embedding) == settings.EMBEDDING_SIZE:
                print("Embedding size matches configuration.")
            else:
                print(f"Warning: Embedding size {len(embedding)} does not match config {settings.EMBEDDING_SIZE}")
        else:
            print("Failed to generate embedding (returned None).")
            
    except Exception as e:
        print(f"Verification failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_embedding())
