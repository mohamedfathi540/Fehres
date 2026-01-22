from .Providers import QdrantDBProvider, PGVectorProvider
from .VectorDBEnums import VectorDBEnums
from Controllers.BaseController import basecontroller
from sqlalchemy.orm import sessionmaker 


class VectorDBProviderFactory :
    
    def __init__(self,config : dict, db_client : sessionmaker ):
        self.config = config
        self.base_controller = basecontroller()
        self.db_client = db_client



    def create (self , provider : str ) :
        if provider == VectorDBEnums.QDRANT.value :
            qdrant_db_client = self.base_controller.get_database_path(db_name = self.config.VECTORDB_PATH)
            return QdrantDBProvider(
                db_client = qdrant_db_client,
                distance_method = self.config.VECTORDB_DISTANCE_METHOD,
                default_vector_size = self.config.EMBEDDING_SIZE,
                index_threshold = self.config.VECTORDB_PGVEC_INDEX_THRESHOLD
            )


        if provider == VectorDBEnums.PGVECTOR.value :
            return PGVectorProvider(
                db_client = self.db_client,
                distance_method = self.config.VECTORDB_DISTANCE_METHOD,
                default_vector_size = self.config.EMBEDDING_SIZE,
                index_threshold = self.config.VECTORDB_PGVEC_INDEX_THRESHOLD,
            )

        return None 