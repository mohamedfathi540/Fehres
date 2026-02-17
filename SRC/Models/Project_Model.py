from .Base_DataModel import BaseDataModel
from .DB_Schemes.minirag.Schemes import Project
from .enums.DataBaseEnum import databaseEnum
from sqlalchemy.future import select
from sqlalchemy import func


 
class projectModel (BaseDataModel) :

    def __init__(self, db_client):
        super().__init__(db_client)
        self.db_client = db_client

    @classmethod
    async def create_instance(cls, db_client : object) :
         instance = cls(db_client)
         return instance

    async def create_project(self, project: Project):

        async with self.db_client() as session :
            async with session.begin() :
                session.add(project)
            await session.commit()
            await session.refresh(project)
        
        return project

    async def get_project_or_create_one(self, project_id: str = None, project_name: str = None):
        """
        Get project by ID or Name, or create if not exists (requires name if creating new).
        If project_id is provided, look up by ID.
        If project_name is provided, look up by Name.
        """
        async with self.db_client() as session :
            async with session.begin() :
                if project_id:
                    query = select(Project).where(Project.project_id == project_id)
                elif project_name:
                    query = select(Project).where(Project.project_name == project_name)
                else:
                    raise ValueError("Either project_id or project_name must be provided")

                result = await session.execute(query)
                project = result.scalar_one_or_none()

                if project is None :
                    if not project_name:
                         # Fallback for legacy default project if needed, or raise error
                         # For now let's assume if we are creating, we MUST have a name.
                         # If it's the default project ID request and it doesn't exist, we might need a default name.
                         if project_id == "1" or project_id == 1:
                             project_name = "Default Project"
                         else:
                             raise ValueError("Cannot create project without a name")

                    project_record = Project(
                        project_name=project_name
                    )
                    # if project_id was passed (e.g. legacy default), we can try to respect it if the DB allows, 
                    # but usually ID is autoincrement. 
                    # ideally we just let ID be auto-generated.
                    
                    project = await self.create_project(project=project_record)
                    return project
                else :
                    return project
                
    async def get_all_projects (self , page : int = 1 ,page_size : int = 10) :

        async with self.db_client() as session :
            async with session.begin() :
                total_documents = await session.execute(select(func.count(Project.project_id)))
                total_documents = total_documents.scalar_one()
                
                if total_documents == 0:
                    return [], 0
                
                total_pages = (total_documents + page_size - 1) // page_size  # Ceiling division

                query = select(Project).offset((page - 1)*page_size).limit(page_size)
                result = await session.execute(query)
                projects = result.scalars().all()
                
                return projects,total_pages

    
         