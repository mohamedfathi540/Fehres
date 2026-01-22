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

    def __init__(self ,genration_client ,embedding_client ,vectordb_client,template_parser) :
        super().__init__()
        self.genration_client = genration_client
        self.embedding_client = embedding_client
        self.vectordb_client = vectordb_client  
        self.template_parser = template_parser


    def create_collection_name (self , project_id  : str) :
        return f"collection_{self.vectordb_client.default_vector_size}_{project_id}".strip()


    async def reset_vector_db_collection (self , project : Project) :
        collection_name = self.create_collection_name(project_id = project.project_id)
        return await self.vectordb_client.delete_collection(collection_name = collection_name)

    async def get_vector_collection_info ( self , project : Project) :
        collection_name = self.create_collection_name(project_id = project.project_id)
        collection_info = await self.vectordb_client.get_collection_info(collection_name = collection_name)

        return json.loads(
                json.dumps(collection_info,default=lambda x: x.__dict__)
        )
       

    async def index_into_vector_db ( self, project : Project , chunks : list [dataChunk] , 
                                chunks_ids: List[int],do_reset : bool = False) :
        
        collection_name = self.create_collection_name(project_id = project.project_id)

        texts = [c.chunk_text for c in chunks]
        metadata = [c.chunk_metadata for c in chunks]
        vectors = self.embedding_client.embed_text(text = texts ,document_type = DocumentTypeEnum.DOCUMENT.value )

        if not vectors:
            return False

        _ = await self.vectordb_client.create_collection(collection_name = collection_name , do_reset = do_reset ,
                                                    embedding_size  = self.embedding_client.embedding_size)

        _ = await self.vectordb_client.insert_many(collection_name = collection_name , 
                                            texts = texts , vectors = vectors , 
                                            metadata = metadata,
                                            record_ids = chunks_ids)

        return True

    async def search_vector_db_collection  (self , project : Project , text : str ,limit : int = 5) :


        query_vector = None
        collection_name = self.create_collection_name(project_id = project.project_id)
        
        vector = self.embedding_client.embed_text(text = text , document_type = DocumentTypeEnum.QUERY.value)

        if not vector or len(vector) == 0 :
            return False

        if isinstance(vector ,list) and len(vector) > 0:
            query_vector = vector[0]

        if not query_vector:
            return False
    
   
        results = await self.vectordb_client.search_by_vector(collection_name = collection_name , 
                                                        vector = query_vector , limit = limit)
        

        if not results or len(results) == 0 :
            return False
 

        return results


    async def answer_rag_question (self , project : Project , query : str ,limit : int = 5) :


        answer, full_prompt ,chat_history = None , None , None

        #step 1 : retrive related document :
        retrieved_documents = await self.search_vector_db_collection(project = project , text = query , limit = limit)

        if not retrieved_documents or len(retrieved_documents) == 0 :
            return answer, full_prompt ,chat_history

        #step 2 : constract LLM prompt :
        system_prompt = self.template_parser.get("rag", "system_prompt")
        document_prompt = "\n".join([
            self.template_parser.get("rag", "document_prompt",
            {
                "doc_num" : idx+1 ,
                "chunk_text" : self.genration_client.process_text(doc.text)
            })
            for idx,doc in enumerate(retrieved_documents)
            ])

        footer_prompt = self.template_parser.get("rag", "footer_prompt",{
            "query" : query
        })

        chat_history = [
            self.genration_client.construct_prompt(
                prompt = system_prompt,
                role = self.genration_client.enums.SYSTEM.value
            )
        ]

        full_prompt = "\n\n".join([document_prompt , footer_prompt])

        answer = self.genration_client.genrate_text(
            prompt = full_prompt,
            chat_history = chat_history
        )

        return answer, full_prompt ,chat_history