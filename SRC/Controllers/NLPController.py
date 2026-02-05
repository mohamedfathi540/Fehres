from .BaseController import basecontroller
from .ProjectController import projectcontroller
from Models.DB_Schemes import Project , dataChunk , RetrivedDocument
from fastapi import UploadFile
from Models import ResponseSignal
import re
import os
from typing import List
from Stores.LLM.LLMEnums import DocumentTypeEnum
from Helpers.Config import get_settings
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

    async def search_vector_db_collection(self, project: Project, text: str, limit: int = 5):
        query_vector = None
        collection_name = self.create_collection_name(project_id=project.project_id)

        vector = self.embedding_client.embed_text(text=text, document_type=DocumentTypeEnum.QUERY.value)

        if not vector or len(vector) == 0:
            return False

        if isinstance(vector, list) and len(vector) > 0:
            query_vector = vector[0]

        if not query_vector:
            return False

        settings = get_settings()
        hybrid_enabled = getattr(settings, "HYBRID_SEARCH_ENABLED", False)
        hybrid_alpha = getattr(settings, "HYBRID_SEARCH_ALPHA", 0.6)
        if hybrid_enabled:
            from Stores.Sparse import BM25Index
            candidate_mult = 2
            dense_limit = max(limit * candidate_mult, 10)
            
            # Get dense search results
            results = await self.vectordb_client.search_by_vector(
                collection_name=collection_name,
                vector=query_vector,
                limit=dense_limit,
            )
            if not results or len(results) == 0:
                return False
            
            # Get BM25 results
            try:
                bm25_hits = BM25Index.search(int(project.project_id), text, top_k=dense_limit)
                bm25_by_id = {int(cid): float(score) for cid, score in bm25_hits}
            except Exception:
                # If BM25 fails, fall back to dense search only
                return results[:limit]
            
            # Normalize BM25 scores to [0, 1] using min-max normalization
            if bm25_by_id:
                bm25_scores = list(bm25_by_id.values())
                bm25_min = min(bm25_scores)
                bm25_max = max(bm25_scores)
                bm25_range = bm25_max - bm25_min if bm25_max > bm25_min else 1.0
            else:
                bm25_min = 0.0
                bm25_range = 1.0
            
            # Normalize dense scores to [0, 1] if needed
            dense_scores = [getattr(doc, "score", 0.0) for doc in results]
            dense_min = min(dense_scores) if dense_scores else 0.0
            dense_max = max(dense_scores) if dense_scores else 1.0
            dense_range = dense_max - dense_min if dense_max > dense_min else 1.0
            
            # Combine scores
            combined = []
            for doc in results:
                cid = getattr(doc, "chunk_id", None)
                if cid is not None:
                    cid = int(cid)
                
                # Normalize dense score to [0, 1]
                dense_score = getattr(doc, "score", 0.0)
                dense_norm = (dense_score - dense_min) / dense_range if dense_range > 0 else 0.0
                
                # Normalize BM25 score to [0, 1]
                bm25_raw = bm25_by_id.get(cid, 0.0)
                bm25_norm = (bm25_raw - bm25_min) / bm25_range if bm25_range > 0 else 0.0
                
                # Combine: alpha * dense + (1-alpha) * bm25
                combined_score = hybrid_alpha * dense_norm + (1.0 - hybrid_alpha) * bm25_norm
                
                combined.append(
                    RetrivedDocument(
                        text=doc.text,
                        score=combined_score,
                        metadata=getattr(doc, "metadata", None),
                        chunk_id=cid,
                    )
                )
            
            # Sort by combined score descending
            combined.sort(key=lambda d: d.score, reverse=True)
            return combined[:limit]

        results = await self.vectordb_client.search_by_vector(
            collection_name=collection_name,
            vector=query_vector,
            limit=limit,
        )

        if not results or len(results) == 0:
            return False

        return results


    async def answer_rag_question (self , project : Project , query : str ,limit : int = 5) :


        answer, full_prompt ,chat_history = None , None , None

        #step 1 : retrive related document :
        retrieved_documents = await self.search_vector_db_collection(project = project , text = query , limit = limit)

        if not retrieved_documents or len(retrieved_documents) == 0 :
            return answer, full_prompt ,chat_history

        #step 2 : constract LLM prompt (include source metadata when available)
        system_prompt = self.template_parser.get("rag", "system_prompt")
        doc_lines = []
        for idx, doc in enumerate(retrieved_documents):
            chunk_text = self.genration_client.process_text(doc.text)
            if getattr(doc, "metadata", None) and isinstance(doc.metadata, dict):
                parts = []
                if doc.metadata.get("source"):
                    parts.append(doc.metadata["source"])
                if doc.metadata.get("page") is not None:
                    parts.append(f"page {doc.metadata['page']}")
                if doc.metadata.get("domain"):
                    parts.append(f"domain: {doc.metadata['domain']}")
                if parts:
                    chunk_text = "From: " + ", ".join(parts) + "\n" + chunk_text
            doc_lines.append(
                self.template_parser.get("rag", "document_prompt", {"doc_num": idx + 1, "chunk_text": chunk_text})
            )
        document_prompt = "\n".join(doc_lines)

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