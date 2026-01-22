from fastapi import FastAPI,APIRouter,Depends,UploadFile,status,Request
from fastapi.responses import JSONResponse
import os
from Helpers.Config import get_settings,settings
from Controllers import datacontroller ,projectcontroller ,processcontroller,NLPController
import aiofiles
from Models import ResponseSignal
import logging
from .Schemes.Date_Schemes import ProcessRequest
from Models.Project_Model import projectModel
from Models.DB_Schemes import dataChunk ,Asset
from Models.Chunk_Model import ChunkModel
from Models.Asset_Model import AssetModel
from Models.enums.AssetTypeEnum import assettypeEnum


logger = logging.getLogger("uvicorn.error")

data_router = APIRouter(
    prefix = "/api/v1/data",
    tags = ["api_v1","data"]

)

@data_router.post("/upload/{project_id}")
async def upload_data (request :Request,project_id : int ,file : UploadFile ,
                       app_settings : settings = Depends(get_settings))  :


    project_model = await projectModel.create_instance(
        db_client=request.app.db_client
    )

    project = await project_model.get_project_or_create_one(
        project_id=project_id
    )

    # validate the file properties

    data_controller = datacontroller()
    is_valid ,result_signal = data_controller.validate_uploaded_file(file = file) 
    
    if not is_valid : 
       return JSONResponse(
           status_code = status.HTTP_400_BAD_REQUEST ,
           content={
                "signal": result_signal        }
           )    
    
    project_dir_path = projectcontroller().get_project_path(project_id = project_id )
    file_path, file_id = data_controller.genrate_unique_filepath(org_filename=file.filename ,project_id=project_id )



    try :
        async with aiofiles.open(file_path, "wb") as f :
            while chunk := await file.read(app_settings.FILE_DEFAULT_CHUNK_SIZE) :
                await f.write(chunk)

    except Exception as E :

        logger.error(f"Error while uploading the file : {E}")
        
        return JSONResponse(
           content={
                "signal": ResponseSignal.FILE_NOT_UPLOADED.value   }
           )    
    
    asset_model = await AssetModel.create_instance(db_client=request.app.db_client)
    asset_resource = Asset(asset_project_id=project.project_id,
                            asset_type=assettypeEnum.FILE.value,
                            asset_name=file_id,
                            asset_size=os.path.getsize(file_path))
    asset_record = await asset_model.create_asset(asset=asset_resource)

    return JSONResponse(
           content={
                "signal": ResponseSignal.FILE_UPLOADED.value,
                "file_id" : str(asset_record.asset_id)             }
           )

@data_router.post("/process/{project_id}")
async def process_endpoint (request :Request ,project_id :int ,process_request : ProcessRequest) :

    chunk_size = process_request.chunk_size
    overlap_size = process_request.overlap_size
    do_reset = process_request.Do_reset

    project_model =await projectModel.create_instance(
        db_client=request.app.db_client
    )

    project = await project_model.get_project_or_create_one(
        project_id=project_id
    )

    asset_model = await AssetModel.create_instance(db_client=request.app.db_client)
    project_files_ids = {}

    nlp_controller = NLPController(
        genration_client=request.app.genration_client,
        embedding_client=request.app.embedding_client,
        vectordb_client=request.app.vectordb_client,
        template_parser=request.app.template_parser 
    )

    if process_request.file_id:
        asset_record = await asset_model.get_asset_record(asset_project_id=project_id,
                                                          asset_name=process_request.file_id)
        if asset_record is None :
            return JSONResponse(
            status_code = status.HTTP_400_BAD_REQUEST ,
            content={
                "signal": ResponseSignal.FILE_ID_ERROR.value})
        
        project_files_ids = {
            asset_record.asset_id : asset_record.asset_name
        }

    else :
        project_files_ids =await asset_model.get_all_project_asset(asset_project_id=project.project_id,
                                                                   asset_type=assettypeEnum.FILE.value)
        project_files_ids ={
            record.asset_id : record.asset_name
            for record in project_files_ids
        }
    
    if len (project_files_ids) == 0 :
        return JSONResponse(
            status_code = status.HTTP_400_BAD_REQUEST ,
            content={
                "signal": ResponseSignal.NO_FILE_ERROR.value})


    Process_Controller = processcontroller(project_id=project_id)   

    no_files = 0
    no_records = 0

    chunk_model = await ChunkModel.create_instance(db_client=request.app.db_client)


    if do_reset == 1 :
        #delete associated vectors collection
        collection_name = nlp_controller.create_collection_name(project_id=project.project_id)
        _ = await request.app.vectordb_client.delete_collection(collection_name=collection_name)
        #delete associated chunks
        _ = await chunk_model.delete_chunk_by_project_id(project_id = project.project_id)

    for asset_id, file_id in project_files_ids.items():
        
        file_content = Process_Controller.get_file_content(file_id=file_id)

        if file_content is None :
            logger.error(f"Error while processing file : {file_id}")
            continue

        file_chunks = Process_Controller.process_file_content(
            file_content = file_content,
            file_id = file_id,
            chunk_size = chunk_size,
            overlap_size = overlap_size
            
        )

        if file_chunks is None or len(file_chunks) == 0:
            return JSONResponse(
            content={
                    "signal": ResponseSignal.PROCESSING_FAILED.value          }
            )

        file_chunks_records = [
            dataChunk(chunk_text = chunk.page_content ,
                    chunk_metadata = chunk.metadata,
                    chunk_order = i+1 ,
                    chunk_project_id = project.project_id ,
                    chunk_asset_id = asset_id
                    )
                    for i,chunk in enumerate(file_chunks)
        ]

        no_records += await chunk_model.insert_many_chunks(chunks = file_chunks_records)
        no_files += 1


    return JSONResponse(
           content={
                "signal": ResponseSignal.PROCESSING_DONE.value ,
                "Inserted_chunks" : no_records ,
                "processed_files" : no_files  })


   


  