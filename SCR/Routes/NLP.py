from fastapi import FastAPI,APIRouter,status,Request
from fastapi.responses import JSONResponse
import logging
from .Schemes.NLP_Schemes import PushRequest , SearchRequest 
from Models.Project_Model import projectModel 
from Models.Chunk_Model import ChunkModel
from Controllers.NLPController import NLPController
from Models.enums.ResponsEnums import ResponseSignal
from tqdm.auto import tqdm

logger = logging.getLogger("uvicorn.error")

nlp_router = APIRouter(
    prefix = "/api/v1/nlp",
    tags = ["api_v1","nlp"]
)

@nlp_router.post("/index/push/{project_id}")
async def index_project (request :Request ,project_id :int ,push_request : PushRequest) :


    # get project
    project_model = await projectModel.create_instance(db_client=request.app.db_client)
    chunk_model = await ChunkModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)
    
    if not project :
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"Signal" : ResponseSignal.PROJECT_NOT_FOUND.value})


    nlp_controller = NLPController(genration_client=request.app.genration_client,
                                    embedding_client=request.app.embedding_client,
                                    vectordb_client=request.app.vectordb_client,
                                    template_parser=request.app.template_parser)

    has_records = True
    page_no = 1
    inserted_items_count = 0



    #create collection if not esixted
    collection_name = nlp_controller.create_collection_name(project_id=project.project_id)
    _ = await request.app.vectordb_client.create_collection(collection_name=collection_name
                                                            ,do_reset=push_request.do_reset
                                                            ,embedding_size=request.app.embedding_client.embedding_size )

    #setup batches
    total_chunks_count = await chunk_model.get_total_chunks_count(project_id=project.project_id)
    p_bar = tqdm(total=total_chunks_count,desc="vectors Indexing",position=0)

    while has_records :

        page_chunks = await chunk_model.get_project_chunks(project_id=project.project_id, page_no=page_no)
        if len (page_chunks) :
            page_no += 1
        if not page_chunks or len(page_chunks) == 0 :
            has_records = False
            break
        chunks_ids = [chunk.chunk_id for chunk in page_chunks]
        
        is_inserted = await nlp_controller.index_into_vector_db(project=project , chunks=page_chunks ,
                                                            chunks_ids=chunks_ids )
        if not is_inserted :
            return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                content={"Signal" : ResponseSignal.INSERT_INTO_VECTOR_DB_ERROR.value})
        
        
        p_bar.update(len(page_chunks))
        inserted_items_count += len(page_chunks)

    p_bar.close()
    return JSONResponse(
        content={"Signal" : ResponseSignal.INSERT_INTO_VECTOR_DB_DONE.value ,
                 "InsertedItemsCount" : inserted_items_count})

@nlp_router.get("/index/info/{project_id}")
async def get_project_index_info (request :Request ,project_id :int) :

    project_model = await projectModel.create_instance(db_client=request.app.db_client)
    chunk_model = await ChunkModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)
    
    if not project :
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"Signal" : ResponseSignal.PROJECT_NOT_FOUND.value})

    nlp_controller = NLPController(genration_client=request.app.genration_client,
                                    embedding_client=request.app.embedding_client,
                                    vectordb_client=request.app.vectordb_client,
                                    template_parser=request.app.template_parser)


    collection_info = await nlp_controller.get_vector_collection_info(project=project)

    return JSONResponse(
        content={"Signal" : ResponseSignal.GET_VECTOR_COLLECTION_INFO_DONE.value ,
                 "CollectionInfo" : collection_info})


@nlp_router.post("/index/search/{project_id}")
async def search_index(request :Request ,project_id :int , search_request : SearchRequest) :
    
    
    project_model = await projectModel.create_instance(db_client=request.app.db_client)
    chunk_model = await ChunkModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)
    
    if not project :
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"Signal" : ResponseSignal.PROJECT_NOT_FOUND.value})

    nlp_controller = NLPController(genration_client=request.app.genration_client,
                                    embedding_client=request.app.embedding_client,
                                    vectordb_client=request.app.vectordb_client,
                                    template_parser=request.app.template_parser)

    results = await nlp_controller.search_vector_db_collection(project=project , 
                                                         text= search_request.text ,
                                                         limit = search_request.limit)

    if not results or len(results) == 0 :
        
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"Signal" : ResponseSignal.SEARCH_INDEX_NOT_FOUND.value})

    return JSONResponse(
        content={"Signal" : ResponseSignal.SEARCH_INDEX_DONE.value ,
                 "Results" : [
                    result.dict()
                    for result in results]
                 })


@nlp_router.post("/index/answer/{project_id}")
async def answer_index(request :Request ,project_id :int , search_request : SearchRequest) :
    
    
    project_model = await projectModel.create_instance(db_client=request.app.db_client)
    chunk_model = await ChunkModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)
    
    if not project :
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND,
                            content={"Signal" : ResponseSignal.PROJECT_NOT_FOUND.value})

    nlp_controller = NLPController(genration_client=request.app.genration_client,
                                    embedding_client=request.app.embedding_client,
                                    vectordb_client=request.app.vectordb_client,
                                    template_parser=request.app.template_parser)


    answer, full_prompt ,chat_history =await nlp_controller.answer_rag_question( project=project , 
                                                                         query=search_request.text , 
                                                                         limit=search_request.limit)

    if not answer :
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            content={"Signal" : ResponseSignal.ANSWER_INDEX_ERROR.value}
                            )

    return JSONResponse(
        content={"Signal" : ResponseSignal.ANSWER_INDEX_DONE.value ,
                 "Answer" : answer,
                 "FullPrompt" : full_prompt,
                 "ChatHistory" : chat_history}
    )
