from fastapi import FastAPI,APIRouter,status,Request
from fastapi.responses import JSONResponse
import logging
from .Schemes.NLP_Schemes import PushRequest
from Models.Project_Model import projectModel

logger = logging.getLogger("uvicorn.error")

nlp_router = APIRouter(
    prefix = "/api/v1/nlp",
    tags = ["api_v1","nlp"]
)

@nlp_router.post("/index/push/{project_id}")
async def index_project (request :Request ,project_id :str ,push_request : PushRequest) :


    # get project
    project_model = await projectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)
    

        