from enum import Enum

class LLMEnums(Enum) :
    OPENAI = "OPENAI"
    COHERE = "COHERE"
    GEMINI = "GEMINI"
<<<<<<< HEAD
=======
    OLLAMA = "OLLAMA"
>>>>>>> d49b326 (-Add Hugging Face as a new LLM provider for text generation and embeddings)
    HUGGINGFACE = "HUGGINGFACE"


class OpenAIEnum(Enum) :
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class CohereEnum(Enum) :
    SYSTEM = "SYSTEM"
    USER = "USER"
    ASSISTANT = "CHATBOT"

    DOCUMENT = "search_document"
    QUERY = "search_query"

class GeminiEnum(Enum) :
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

<<<<<<< HEAD
=======
class OllamaEnum(Enum) :
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class HuggingFaceEnum(Enum) :
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

>>>>>>> d49b326 (-Add Hugging Face as a new LLM provider for text generation and embeddings)
class DocumentTypeEnum(Enum) :
    DOCUMENT = "document"
    QUERY = "query"
    