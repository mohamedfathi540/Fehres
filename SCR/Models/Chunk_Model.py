from .Base_DataModel import BaseDataModel
from .DB_Schemes import dataChunk
from .enums.DataBaseEnum import databaseEnum
from bson.objectid import ObjectId
from pymongo import InsertOne
from sqlalchemy.future import select
from sqlalchemy import func ,delete



class ChunkModel (BaseDataModel) :
    def __init__(self, db_client : str) : 
        super().__init__(db_client = db_client)
        self.db_client = db_client

    @classmethod
    async def create_instance(cls, db_client : object) :
         instance = cls(db_client)
         return instance


    async def create_chunk(self ,chunk : dataChunk) :


        async with self.db_client() as session :
            async with session.begin() :
                session.add(chunk)
            await session.commit()
            await session.refresh(chunk)
        
        return chunk
    
    
    async def get_chunk(self,chunk_id : str) :
       
       async with self.db_client() as session :
            result = await session.execute(select(dataChunk).where(dataChunk.chunk_id == chunk_id))
            chunck = result.scalar_one_or_none()
            return chunck
       
    async def insert_many_chunks (self,chunks : list ,batch_size : int = 10) :
        
        async with self.db_client() as session :
            async with session.begin() :
                for i in range (0,len(chunks),batch_size) :
                    batch = chunks[i:i+batch_size]
                    session.add_all(batch)
            await session.commit()
        return len(chunks)
    
    async def delete_chunk_by_project_id(self, project_id : ObjectId) :
        
        async with self.db_client() as session :
            async with session.begin() :
                stmt = delete(dataChunk).where(dataChunk.chunk_project_id == project_id)
                result = await session.execute(stmt)
                await session.commit()
        
        return result.rowcount
     
    async def get_project_chunks (self, project_id : ObjectId , page_no : int = 1 , page_size : int = 50) :
        
        async with self.db_client() as session :
            async with session.begin() :
                stmt = select(dataChunk).where(dataChunk.chunk_project_id == project_id).offset((page_no - 1)*page_size).limit(page_size)
                
                result = await session.execute(stmt)
                records = result.scalars().all()
            return records
        

    async def get_total_chunks_count (self, project_id : ObjectId) :
        total_count = 0
        async with self.db_client() as session :
            async with session.begin() :
                count_sql = select(func.count(dataChunk.chunk_id)).where(dataChunk.chunk_project_id == project_id)
                records_count = await session.execute(count_sql)
                total_count = records_count.scalar()

            return total_count