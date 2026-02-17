from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List, Optional


def _env_bool(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "on")
    return bool(v)


class settings (BaseSettings):

    APP_NAME: str 
    APP_VERSION: str

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
 
    OPENAI_API_KEY : Optional[str] = None
    OPENAI_BASE_URL : Optional[str] = None
    COHERE_API_KEY : Optional[str] = None
    GEMINI_API_KEY : Optional[str] = None
    GEMINI_API_VERSION : str = "v1"
    OLLAMA_BASE_URL : Optional[str] = None
    HUGGINGFACE_API_KEY : Optional[str] = None

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


    # Chunking defaults for learning books (large references)
    LEARNING_BOOKS_CHUNK_SIZE : int = 2000
    LEARNING_BOOKS_OVERLAP_SIZE : int = 200

    # Documentation chunking defaults (backend-controlled)
    DOC_CHUNK_SIZE : int = 1000
    DOC_OVERLAP_SIZE : int = 200

    # Optional JSON mapping of filename (or pattern) to domain for chunk metadata e.g. {"statistics.pdf": "statistics", "ml-intro.pdf": "ml"}
    BOOK_DOMAIN_MAPPING : Optional[str] = None

    # Hybrid search (dense + BM25): 0 = only BM25, 1 = only dense
    HYBRID_SEARCH_ENABLED : bool = True
    HYBRID_SEARCH_ALPHA : float = 0.6

    # BM25 index persistence directory (default: under SRC/data/bm25)
    BM25_INDEX_DIR : Optional[str] = None

    # Web scraping configuration
    SCRAPING_MAX_PAGES : int = 1000
    SCRAPING_RATE_LIMIT : float = 0.5
    SCRAPING_USER_AGENT : str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    SCRAPING_TIMEOUT : int = 120
    SCRAPING_DEBUG : bool = False
    SCRAPING_USE_BROWSER : bool = True
    SCRAPING_IGNORE_ROBOTS : bool = False
    SCRAPING_CONCURRENCY : int = 1
    SCRAPING_EMBED_BATCH_SIZE : int = 50
    SCRAPING_EMBED_DURING : bool = False
    SCRAPING_AUTO_INDEX : bool = True

    # Default project ID for single-project system
    DEFAULT_PROJECT_ID : int = 1

    @field_validator("SCRAPING_DEBUG", "SCRAPING_USE_BROWSER", "SCRAPING_IGNORE_ROBOTS", "SCRAPING_AUTO_INDEX", mode="before")
    @classmethod
    def parse_scraping_bool(cls, v):
        return _env_bool(v) if v is not None else False

    model_config = SettingsConfigDict(env_file=".env")

def get_settings () :
    return settings()
