from fastapi import FastAPI,APIRouter,status,Request
from fastapi.responses import JSONResponse
import logging
from .Schemes.NLP_Schemes import PushRequest
from Models.Project_Model import projectModel 
from Models.Chunk_Model import ChunkModel
from Controllers.NLPController import NLPController
from Models.enums.ResponsEnums import ResponseSignal
logger = logging.getLogger("uvicorn.error")

nlp_router = APIRouter(
    prefix = "/api/v1/nlp",
    tags = ["api_v1","nlp"]
)

@nlp_router.post("/index/push/{project_id}")
async def index_project (request :Request ,project_id :str ,push_request : PushRequest) :


    # get project
    project_model = await projectModel.create_instance(db_client=request.app.db_client)
    chunk_model = await ChunkModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)
    
    if not project :
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"Signal" : ResponseSignal.PROJECT_NOT_FOUND.value})


    nlp_controller = NLPController(genration_client=request.app.genration_client,
                                    embedding_client=request.app.embedding_client,
                                    vectordb_client=request.app.vectordb_client)

    has_records = True
    page_no = 1
    inserted_items_count = 0
    while has_records :
        page_chunks = await chunk_model.get_project_chunks(project_id=project.id, page_no=page_no)
        if len (page_chunks) :
            page_no += 1
        if not page_chunks or len(page_chunks) == 0 :
            has_records = False
            break
        
        is_inserted = nlp_controller.index_into_vector_db(project=project , chunks=page_chunks ,
                                                            do_reset=push_request.do_reset)
        if not is_inserted :
            return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                content={"Signal" : ResponseSignal.INSERT_INTO_VECTOR_DB_ERROR.value})
        
        inserted_items_count += len(page_chunks)

    return JSONResponse(
        content={"Signal" : ResponseSignal.INSERT_INTO_VECTOR_DB_DONE.value ,
                 "InsertedItemsCount" : inserted_items_count})

