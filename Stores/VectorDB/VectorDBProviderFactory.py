from .Providers import QdrantDBProvider
from .VectorDBEnums import VectorDBEnums
from Controllers.BaseController import basecontroller



class VectorDBProviderFactory :
    def __init__(self,config : dict):
        self.config = config
        self.base_controller = basecontroller()
    def create (self , provider : str ) :
        if provider == VectorDBEnums.QDRANT.value :
            db_path = self.base_controller.get_database_path(db_name = self.config.VECTORDB_PATH)


            return QdrantDBProvider(
                db_path = db_path,
                distance_method = self.config.VECTORDB_DISTANCE_METHOD,
            )
        return None 