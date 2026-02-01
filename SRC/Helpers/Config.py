from pydantic_settings import BaseSettings ,SettingsConfigDict
from typing import List, Optional

class settings (BaseSettings):

    APP_NAME: str 
    APP_VERSION: str
    OPENAI_API_KEY: str

    FILE_ALLOWED_TYPES :list
    FILE_MAX_SIZE :int
    FILE_DEFAULT_CHUNK_SIZE :int

    POSTGRES_USER : str
    POSTGRES_PASSWORD : str
    POSTGRES_HOST : str
    POSTGRES_PORT : str
    POSTGRES_MAIN_DB : str

    
    GENRATION_BACKEND : str
    EMBEDDING_BACKEND : str
 
    OPENAI_API_KEY : str = None
    OPENAI_BASE_URL : str = None
    COHERE_API_KEY : str = None
    GEMINI_API_KEY : str = None

    GENRATION_MODEL_ID_LITERAL : List[str] = None
    EMBEDDING_MODEL_ID_LITERAL : List[str] = None
    GENRATION_MODEL_ID : str = None
    EMBEDDING_MODEL_ID : str = None
    EMBEDDING_SIZE : int = None


    INPUT_DEFUALT_MAX_CHARACTERS : int = None
    GENRATED_DEFUALT_MAX_OUTPUT_TOKENS : int = None
    GENRATION_DEFUALT_TEMPERATURE : float = None 

    VECTORDB_BACKEND_LITERAL : List[str] = None
    VECTORDB_BACKEND : str 
    VECTORDB_PATH : str
    VECTORDB_DISTANCE_METHOD : str = None
    VECTORDB_PGVEC_INDEX_THRESHOLD : int = 4


    DEFUALT_LANGUAGE : str = "en"
    PRIMARY_LANGUAGE : str = "en"

    # Learning books corpus: fixed project ID reserved for AI/Data Science references (maths, statistics, coding, ml, dl, genai, system_design)
    LEARNING_BOOKS_PROJECT_ID : int = 10

    # Chunking defaults for learning books (large references)
    LEARNING_BOOKS_CHUNK_SIZE : int = 2000
    LEARNING_BOOKS_OVERLAP_SIZE : int = 200

    # Optional JSON mapping of filename (or pattern) to domain for chunk metadata e.g. {"statistics.pdf": "statistics", "ml-intro.pdf": "ml"}
    BOOK_DOMAIN_MAPPING : Optional[str] = None

    # Hybrid search (dense + BM25): 0 = only BM25, 1 = only dense
    HYBRID_SEARCH_ENABLED : bool = True
    HYBRID_SEARCH_ALPHA : float = 0.6

    # BM25 index persistence directory (default: under SRC/data/bm25)
    BM25_INDEX_DIR : Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env")

def get_settings () :
    return settings()
