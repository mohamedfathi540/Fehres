from enum import Enum

class LLMEnums(Enum) :
    OPENAI = "OPENAI"
    COHERE = "COHERE"
    GEMINI = "GEMINI"
    OLLAMA = "OLLAMA"
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

class OllamaEnum(Enum) :
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class HuggingFaceEnum(Enum) :
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class DocumentTypeEnum(Enum) :
    DOCUMENT = "document"
    QUERY = "query"
    