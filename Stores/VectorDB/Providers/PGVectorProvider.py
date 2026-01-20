from sqlalchemy.sql._elements_constructors import false
from ..VectorDBInterface import VectorDBInterface
from ..VectorDBEnums import (DistanceMethodEnums, PgVectorTableSchemeEnums, 
                        PgvectorDistanceMethodEnums, PgvectorIndexTypeEnums)
from sqlalchemy.sql import text as sql_text
import logging
from typing import List, Dict, Any, Optional
from Models.DB_Schemes import RetrivedDocument
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine
import json, uuid

class PGVectorProvider(VectorDBInterface):
    def __init__(self, db_client ,defualt_vector_size : int = 786
                , distance_method: str = None , index_threshold : int = 10000):
        self.db_client = db_client
        self.defualt_vector_size = defualt_vector_size
        self.distance_method = distance_method
        self.index_threshold = index_threshold


        self.pgvector_table_prefix = PgVectorTableSchemeEnums._PREFIX.value

        self.logger = logging.getLogger("uvicorn")

        self.defualt_index_name = lambda (collection_name): f"{collection_name}_vector_idx"

    async def connect(self):
        try:
            async with self.db_client() as session:
                async with session.begin():
                    await session.execute(sql_text("CREATE EXTENSION IF NOT EXISTS vector"))
                    await session.commit()

        except Exception as e:
            self.logger.error(f"Failed to connect to PGVector DB: {e}")
            raise e


    async def disconnect(self):
        pass
        

    async def is_collection_exists(self, collection_name: str) -> bool:
        try:
            record = None
            async with self.db_client() as session:
                async with session.begin():
                    list_tbl = sql_text('SELECT * FROM pg_tables WHERE tablename = :collection_name')
                    results = await session.execute(list_tbl, {"collection_name": collection_name})
                    record = results.scalar_one_or_none()
            return record is not None

        except Exception as e:
            self.logger.error(f"Failed to check if collection exists: {e}")
            raise e
    

    async def list_all_collections(self) -> List[str]:
        try:
            records = []
            async with self.db_client() as session:
                async with session.begin():
                    list_tbl = sql_text('SELECT tablename FROM pg_tables WHERE tablename LIKE :prefix')
                    results = await session.execute(list_tbl,{"prefix" : self.pgvector_table_prefix})
                    records = results.scalars().all()
            return records   

        except Exception as e:
            self.logger.error(f"Failed to list all collections: {e}")
            raise e


    async def get_collection_info(self, collection_name: str) -> dict:
       async with self.db_client() as session:
               try:
                async with session.begin():
                    table_inf_sql = sql_text('''
                    SELECT schemaname, tablename,tableowner, tablespace, hasindexes
                    FROM pg_tables
                    WHERE table_name = :collection_name
                    ''')
                     
                    count = sql_text(f'SELECT COUNT(*) FROM {collection_name}')
                    table_info = await session.execute(table_inf_sql, {"collection_name": collection_name})
                    record_count = await session.execute(count,{"collection_name": collection_name})

                    table_data = table_info.fetchone()
                    if not table_data:
                        return None

                    return {
                        "table_info": dict(table_data),
                        "record_count": record_count
                    }

                except Exception as e:
                    self.logger.error(f"Failed to get collection info: {e}")
                    raise e


    async def delete_collection(self, collection_name: str):
        try:
            async with self.db_client() as session:
                async with session.begin():
                    self.logger.info(f"Deleting collection: {collection_name}")
                    delete_tbl = sql_text('DROP TABLE IF EXISTS :collection_name')
                    await session.execute(delete_tbl, {"collection_name": collection_name})
                    await session.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete collection: {e}")
            raise e


    async def create_collection(self, collection_name: str, embedding_size: int, do_reset: bool = False):
        try:
            if do_reset:
                _ = await self.delete_collection(collection_name = collection_name)
            
            is_collection_exists = await self.is_collection_exists(collection_name = collection_name)
            if not is_collection_exists:
                self.logger.info(f"Creating collection: {collection_name}")
                async with self.db_client() as session:
                    async with session.begin():
                        create_sql = sql_text(f'CREATE TABLE {collection_name} ('
                                            f'{PgVectorTableSchemeEnums.ID.value} bigserial PRIMARY KEY, '
                                            f'{PgVectorTableSchemeEnums.TEXT.value} text, '
                                            f'{PgVectorTableSchemeEnums.VECTORS.value} vector({embedding_size}), '
                                            f'{PgVectorTableSchemeEnums.METADATA.value} jsonb DEFAULT \'{{}}\', '
                                            f'{PgVectorTableSchemeEnums.CHUNK_ID.value} integer,'
                                            f'FOREIGN KEY ({PgVectorTableSchemeEnums.CHUNK_ID.value}) REFERENCES chunks(chunk_id) '
                                            ')'
                                            )
                        await session.execute(create_sql)
                        await session.commit()
                return True
            return False
        
        except Exception as e:
            self.logger.error(f"Failed to create collection: {e}")
            raise e
        


    async def is_index_exsited (self,collection_name: str) -> bool:
        try:
            index_name = self.defualt_index_name(collection_name = collection_name)
            async with self.db_client() as session:
                    async with session.begin():
                        check_sql = sql_text("""
                            SELECT 1 FROM pg_indexes
                            WHERE tablename = :table_name
                            AND indexname = :index_name
                        """)
                        
                        results = await session.execute(check_sql, {"table_name": collection_name,
                                                                     "index_name": index_name})
                        record = bool(results.scalar_one_or_none())
                        
                        return record
        except Exception as e:
            self.logger.error(f"Failed to check index: {e}")
            raise e



    async def create_index_vector (self,collection_name :str ,
                                   index_type : str = PgvectorIndexTypeEnums.HNSW.value):

        try : 
            is_index_exsited = await self.is_index_exsited(collection_name = collection_name)
            if is_index_exsited:
                self.logger.info(f"Index already exists for collection: {collection_name}")
                return True


            async with self.db_client() as session:
                    async with session.begin():
                        count_sql = sql_text(f"SELECT COUNT(*) FROM {collection_name}")
                        result = await session.execute(count_sql)
                        records_count = result.scalar_one()
                        
                        if records_count < self.index_threshold :
                            return False

                        self.logger.info(f"Start:Creating index for collection: {collection_name}")

                        index_name = self.defualt_index_name(collection_name)
                        create_idx_sql = sql_text(
                                                    f'CREATE INDEX {index_name} ON {collection_name} '
                                                     f'USING {index_type} ({PgVectorTableSchemeEnums.VECTORS.value} {self.distance_method})'
                                                     )
                        await session.execute(create_idx_sql)

                        self.logger.info(f"end:Creating index for collection: {collection_name}")

            
        except Exception as e:
            self.logger.error(f"Failed to create index for collection: {collection_name}: {e}")
            raise e
                
    async def reset_vector_index (self, collection_name : str, 
                                index_type : str = PgvectorIndexTypeEnums.HNSW.value) -> bool:
        try:
            index_name = self.defualt_index_name(collection_name)
            async with self.db_client() as session:
                async with session.begin():
                    drop_sql = sql_text(f'DROP INDEX IF EXISTS {index_name}')
                    await session.execute(drop_sql)
                    
            return await self.create_index_vector(collection_name = collection_name, index_type = index_type)


        except Exception as e:
            self.logger.error(f"Failed to reset index for collection: {collection_name}: {e}")
            raise e


    async def insert_one(self, collection_name: str, 
                   text: str, vector: list, 
                   metadata: dict = None, 
                   record_id: str = None):
        try:
            is_collection_exists = await self.is_collection_exists(collection_name = collection_name)
            if not is_collection_exists:
                self.logger.info(f"Can not insert record to non existing collection: {collection_name}")
                return False
            
            if not record_id:
                self.logger.info(f"Can not insert new record without chunk_id: {collection_name}")
                return False

            async with self.db_client() as session:
                async with session.begin():

                    insert_sql = sql_text(f'INSERT INTO {collection_name} '
                    f'({PgVectorTableSchemeEnums.TEXT.value},{PgVectorTableSchemeEnums.VECTORS.value},{PgVectorTableSchemeEnums.METADATA.value},{PgVectorTableSchemeEnums.CHUNK_ID.value}) '
                    f'VALUES (:text, :vector, :metadata, :chunk_id)'
                    )

                    await session.execute(insert_sql, 
                        {
                        "text": text,
                        "vector": "[" +",".join([str(v) for v in vector ])+ "]",
                        "metadata": metadata,
                        "chunk_id": record_id
                        }
                    )
                    await session.commit()

            return True
       
            
        except Exception as e:
            self.logger.error(f"Error inserting one record to collection: {collection_name}, error: {e}")
            return False

    async def insert_many(self, collection_name: str, 
                    texts: list, vectors: list, 
                    metadata: list = None, 
                    record_ids: list = None, batch_size: int = 50):

        try:
            is_collection_exists = await self.is_collection_exists(collection_name = collection_name)
            if not is_collection_exists:
                self.logger.info(f"Can not insert records to non existing collection: {collection_name}")
                return False
            if len(vectors) != len(record_ids):
                self.logger.info(f"Invalid data items for collection: {collection_name}")
                return False
            if not metadata or len(metadata) == 0:
                metadata = [None] * len(texts)
            if not record_ids or len(record_ids) == 0:
                record_ids = None

            async with self.db_client() as session:
                async with session.begin():
                    for i in range(0,len(texts),batch_size):
                        batch_texts = texts[i:i+batch_size]
                        batch_vectors = vectors[i:i+batch_size]
                        batch_metadata = metadata[i:i+batch_size] 
                        batch_record_ids = record_ids[i:i+batch_size]
                        values = []

                        for _text, _vector, _metadata, _record_id in zip(batch_texts, batch_vectors, batch_metadata, batch_record_ids):
                            values.append({
                                "text": _text,
                                "vector": "[" +",".join([str(v) for v in _vector ])+ "]",
                                "metadata": _metadata,
                                "chunk_id": _record_id
                            })

                            batch_insert_sql = sql_text(f'INSERT INTO {collection_name} '
                                                         f'{PgVectorTableSchemeEnums.TEXT.value}, '
                                                         f'{PgVectorTableSchemeEnums.VECTORS.value}, '
                                                         f'{PgVectorTableSchemeEnums.METADATA.value}, '
                                                         f'{PgVectorTableSchemeEnums.CHUNK_ID.value}) '
                                                         f'VALUES (:text, :vector, :metadata, :chunk_id)'
                                                         )
                            await session.execute(batch_insert_sql, values)
                            await session.commit()
            return True
       
            
        except Exception as e:
            self.logger.error(f"Error inserting many records: {e}")
            return False
        

    async def search_by_vector(self, collection_name: str, vector: list, limit: int = 5) -> List[RetrivedDocument]:
  
        try:
            
            is_collection_exists = await self.is_collection_exists(collection_name = collection_name)
            if not is_collection_exists:
                self.logger.info(f"Can not search for records in a non existing collection: {collection_name}")
                return False
            vector = "[" +",".join([str(v) for v in _vector ])+ "]"

            async with self.db_client() as session:
                async with session.begin():
                    search_sql = sql_text(f'SELECT {PgVectorTableSchemeEnums.TEXT.value} as text,1 -  ({PgVectorTableSchemeEnums.VECTORS.value} <=> :vector) as score',
                    f'FROM {collection_name}'
                     'ORDER BY score DESC '
                     f'LIMIT :{limit}')

                    result = await session.execute(search_sql, {"vector": vector})
                    records = result.fetchall()

                    return [
                        RetrivedDocument(text=record.text,score=record.score)
                        for record in records:
                            ]

        except Exception as e:
            self.logger.error(f"Error searching by vector: {e}")
            return []
