from .Base_DataModel import BaseDataModel
from .DB_Schemes.project import Project
from .enums.DataBaseEnum import databaseEnum


class projectModel (BaseDataModel) :

    def __init__(self, db_client):
        super().__init__(db_client)
        self.collection = self.db_client[databaseEnum.COLLECTION_PROJECT_NAME.value]

    @classmethod
    async def create_instance(cls, db_client : object) :
         instance = cls(db_client)
         await instance.init_collection()
         return instance

    async def init_collection (self) :
        all_collection = await self.db_client.list_collection_names()
        if databaseEnum.COLLECTION_PROJECT_NAME.value not in all_collection :
            self.collection = self.db_client[databaseEnum.COLLECTION_PROJECT_NAME.value]
            indexes = Project.get_indexes()
            for index in indexes :
                await self.collection.create_index(
                    index["key"],
                    name = index["name"],
                    unique = index["unique"]
                )


    async def create_project(self, Project: Project):

        result = await self.collection.insert_one(Project.dict(by_alias=True, exclude_unset=True))
        Project.id = result.inserted_id

        return Project

    async def get_project_or_create_one(self, project_id: str):

        record = await self.collection.find_one({
            "project_id": project_id
        })

        if record is None:
            # create new project
            project = Project(project_id=project_id)
            project = await self.create_project(project=project)

            return project
        
        return Project(**record)
    

    async def get_all_projects (self , page : int = 1 ,page_size : int = 10) :

            #count the total number of Documents

            total_documents = await self.collection.count_doccuments({})

            #calculate the total pages 

            total_pages = total_documents // page_size
            if total_documents % total_pages > 0 :
                 total_pages += 1

            cursur = self.collection.find().skip((page - 1)*page_size).limit(page_size)
            projects = []
            async for document in cursur : 
                 projects.append(
                      
                      Project(**document)
                 )
                
            return projects ,total_pages
         