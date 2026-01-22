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
    def __init__(self, db_client, default_vector_size: int = 786, distance_method: str = None, index_threshold: int = 10000):
        self.db_client = db_client
        self.default_vector_size = default_vector_size
        self.distance_method = distance_method
        if distance_method == DistanceMethodEnums.COSINE.value:
            self.distance_method = PgvectorDistanceMethodEnums.COSINE.value
        elif distance_method == DistanceMethodEnums.DOT.value:
             self.distance_method = PgvectorDistanceMethodEnums.DOT.value
        else:
            self.distance_method = distance_method
            
        self.index_threshold = index_threshold

        self.pgvector_table_prefix = PgVectorTableSchemeEnums._PREFIX.value
        self.logger = logging.getLogger("uvicorn")
        self.default_index_name = lambda collection_name: f"{collection_name}_vector_idx"

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
                    results = await session.execute(list_tbl, {"prefix": self.pgvector_table_prefix})
                    records = results.scalars().all()
            return records   
        except Exception as e:
            self.logger.error(f"Failed to list all collections: {e}")
            raise e

    async def get_collection_info(self, collection_name: str) -> dict:
        async with self.db_client() as session:
            async with session.begin():
                table_inf_sql = sql_text(f'''SELECT schemaname, tablename,tableowner, tablespace, hasindexes
                FROM pg_tables
                WHERE tablename = :collection_name
                ''')
                 
                count_sql    = sql_text(f'SELECT COUNT(*) FROM {collection_name}')
                table_info   = await session.execute(table_inf_sql , {"collection_name": collection_name})
                record_count = await session.execute(count_sql)

                table_data = table_info.fetchone()
                if not table_data:
                    return None

                return {
                    "table_info": {
                        "schema_name": table_data[0],
                        "table_name": table_data[1],
                        "table_owner": table_data[2],
                        "table_space": table_data[3],
                        "has_indexes": table_data[4]
                    },
                    "record_count": record_count.scalar_one()
                }

    async def delete_collection(self, collection_name: str):
        async with self.db_client() as session:
            async with session.begin():
                self.logger.info(f"Deleting collection: {collection_name}")

                delete_tbl = sql_text(f'DROP TABLE IF EXISTS {collection_name}')
                await session.execute(delete_tbl)
                await session.commit()
        return True

    async def create_collection(self, collection_name: str, embedding_size: int, do_reset: bool = False):

        if do_reset:
            _ = await self.delete_collection(collection_name=collection_name)
        
        is_collection_exists = await self.is_collection_exists(collection_name=collection_name)
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

    async def is_index_exsited(self, collection_name: str) -> bool:
        index_name = self.default_index_name(collection_name=collection_name)
        async with self.db_client() as session:
            async with session.begin():
                check_sql = sql_text(f"""
                    SELECT 1 FROM pg_indexes
                    WHERE tablename = :collection_name  
                    AND indexname = :index_name
                """)
                
                results = await session.execute(check_sql , {"collection_name": collection_name , "index_name": index_name})
                record = bool(results.scalar_one_or_none())
                return record

    async def create_index_vector(self, collection_name: str, index_type: str = PgvectorIndexTypeEnums.HNSW.value):
        is_index_exsited = await self.is_index_exsited(collection_name=collection_name)
        if is_index_exsited:
            self.logger.info(f"Index already exists for collection: {collection_name}")
            return True

        async with self.db_client() as session:
            async with session.begin():
                count_sql = sql_text(f"SELECT COUNT(*) FROM {collection_name}")
                result = await session.execute(count_sql)
                records_count = result.scalar_one()
                
                if records_count < self.index_threshold:
                    return False

                self.logger.info(f"Start:Creating index for collection: {collection_name}")

                index_name = self.default_index_name(collection_name)
                create_idx_sql = sql_text(
                                            f'CREATE INDEX {index_name} ON {collection_name} '
                                            f'USING {index_type} ({PgVectorTableSchemeEnums.VECTORS.value} {self.distance_method})'
                                            )
                await session.execute(create_idx_sql)

                self.logger.info(f"end:Creating index for collection: {collection_name}")

    async def reset_vector_index(self, collection_name: str, index_type: str = PgvectorIndexTypeEnums.HNSW.value) -> bool:
        index_name = self.default_index_name(collection_name)
        async with self.db_client() as session:
            async with session.begin():
                drop_sql = sql_text(f'DROP INDEX IF EXISTS {index_name}')
                await session.execute(drop_sql)
                
        return await self.create_index_vector(collection_name=collection_name, index_type=index_type)

    async def insert_one(self, collection_name: str, text: str, vector: list, metadata: dict = None, record_id: str = None):
        is_collection_exists = await self.is_collection_exists(collection_name=collection_name)
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
                metadata_json = json.dumps(metadata,ensure_ascii=False) if metadata is not None else "{}"
                await session.execute(insert_sql, 
                    {
                    "text": text,
                    "vector": "[" + ",".join([str(v) for v in vector]) + "]",
                    "metadata": metadata_json,
                    "chunk_id": record_id
                    }
                )
                await session.commit()
        await self.create_index_vector(collection_name=collection_name)
        return True

    async def insert_many(self, collection_name: str, texts: list, vectors: list, metadata: list = None, record_ids: list = None, batch_size: int = 50):
        is_collection_exists = await self.is_collection_exists(collection_name=collection_name)
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
                for i in range(0, len(texts), batch_size):
                    batch_texts = texts[i:i+batch_size]
                    batch_vectors = vectors[i:i+batch_size]
                    batch_metadata = metadata[i:i+batch_size] 
                    batch_record_ids = record_ids[i:i+batch_size]
                    values = []

                    for _text, _vector, _metadata, _record_id in zip(batch_texts, batch_vectors, batch_metadata, batch_record_ids):
                        metadata_json = json.dumps(_metadata,ensure_ascii=False) if _metadata is not None else "{}"
                        values.append({
                            "text": _text,
                            "vector": "[" + ",".join([str(v) for v in _vector]) + "]",
                            "metadata": metadata_json,
                            "chunk_id": _record_id
                        })

                        # Note: This query preparation being inside the loop is inefficient if strict SQL alchemy, but logic wise mostly fine. 
                        # However, for batch insert, we should execute ONCE per batch if using values list? 
                        # The original code executed inside the loop but with 'values' list which grew? No, 'values' is reset per batch.
                        # Wait, original code: `values.append(...)` then `await session.execute(..., values)`.
                        # This executes ONE INSERT with MULTIPLE VALUES? No, SQLAlchemy execute with list of dicts does executemany.
                    
                    batch_insert_sql = sql_text(f'INSERT INTO {collection_name} '
                                                    f'({PgVectorTableSchemeEnums.TEXT.value}, '
                                                    f'{PgVectorTableSchemeEnums.VECTORS.value}, '
                                                    f'{PgVectorTableSchemeEnums.METADATA.value}, '
                                                    f'{PgVectorTableSchemeEnums.CHUNK_ID.value}) '
                                                    f'VALUES (:text, :vector, :metadata, :chunk_id)'
                                                    )
                    await session.execute(batch_insert_sql, values)
                    await session.commit()
        await self.create_index_vector(collection_name=collection_name)
        return True

    async def search_by_vector(self, collection_name: str, vector: list, limit: int = 5) -> List[RetrivedDocument]:
        is_collection_exists = await self.is_collection_exists(collection_name=collection_name)
        if not is_collection_exists:
            self.logger.info(f"Can not search for records in a non existing collection: {collection_name}")
            return []

        vector_str = "[" + ",".join([str(v) for v in vector]) + "]"

        async with self.db_client() as session:
            async with session.begin():
                search_sql = sql_text(f'SELECT {PgVectorTableSchemeEnums.TEXT.value} as text, 1 - ({PgVectorTableSchemeEnums.VECTORS.value} <=> :vector) as score '
                                      f'FROM {collection_name} '
                                      f'ORDER BY score DESC '
                                      f'LIMIT :limit')

                result = await session.execute(search_sql, {"vector": vector_str, "limit": limit})
                records = result.fetchall()

                return [
                    RetrivedDocument(text=record.text, score=record.score)
                    for record in records
                ]
