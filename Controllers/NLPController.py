from .BaseController import basecontroller
from .ProjectController import projectcontroller
from Models.DB_Schemes import Project ,dataChunk
from fastapi import UploadFile
from Models import ResponseSignal
import re
import os
from typing import List
from Stores.LLM.LLMEnums import DocumentTypeEnum
import json




class NLPController (basecontroller) : 

    def __init__(self ,genration_client ,embedding_client ,vectordb_client) :
        super().__init__()
        self.genration_client = genration_client
        self.embedding_client = embedding_client
        self.vectordb_client = vectordb_client  


    def create_collection_name (self , project_id  : str) :
        return f"collection_{project_id}".strip()


    def reset_vector_db_collection (self , project : Project) :
        collection_name = self.create_collection_name(project_id = project.project_id)
        return self.vectordb_client.delete_collection(collection_name = collection_name)

    def get_vector_collection_info ( self , project : Project) :
        collection_name = self.create_collection_name(project_id = project.project_id)
        collection_info = self.vectordb_client.get_collection_info(collection_name = collection_name)

        return json.loads(
                json.dumps(collection_info,default=lambda x: x.__dict__)
        )
       

    def index_into_vector_db ( self, project : Project , chunks : list [dataChunk] , 
                                chunks_ids: List[int],do_reset : bool = False) :
        
        collection_name = self.create_collection_name(project_id = project.project_id)

        texts = [c.chunk_text for c in chunks]
        metadata = [c.chunk_metadata for c in chunks]
        vectors = [
            self.embedding_client.embed_text(text = text , document_type = DocumentTypeEnum.DOCUMENT.value)
            for text in texts
                  ]

        _ = self.vectordb_client.create_collection(collection_name = collection_name , do_reset = do_reset ,
                                                    embedding_size  = self.embedding_client.embedding_size)

        _ = self.vectordb_client.insert_many(collection_name = collection_name , 
                                            texts = texts , vectors = vectors , 
                                            metadata = metadata,
                                            record_ids = chunks_ids)

        return True

    def search_vector_db_collection  (self , project : Project , text : str ,limit : int = 5) :

        collection_name = self.create_collection_name(project_id = project.project_id)
        

        vector = self.embedding_client.embed_text(text = text , document_type = DocumentTypeEnum.QUERY.value)

        if not vector or len(vector) == 0 :
            return False

    
        results = self.vectordb_client.search_by_vector(collection_name = collection_name , 
                                                        vector = vector , limit = limit)
        

        if not results or len(results) == 0 :
            return []


        return json.loads(
                json.dumps(results,default=lambda x: x.__dict__)
        )
        