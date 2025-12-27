from fastapi import FastAPI,APIRouter,Depends,UploadFile,status,Request
from fastapi.responses import JSONResponse
import os
from Helpers.Config import get_settings,settings
from Controllers import datacontroller ,projectcontroller ,processcontroller
import aiofiles
from Models import ResponseSignal
import logging
from .Schemes.Date_Schemes import ProcessRequest
from Models.Project_Model import projectModel
from Models.DB_Schemes import dataChunk
from Models.Chunk_Model import ChunkModel

logger = logging.getLogger("uvicorn error")

data_router = APIRouter(
    prefix = "/api/v1/data",
    tags = ["api_v1","data"]

)

@data_router.post("/upload/{project_id}")
async def upload_data (request :Request,project_id : str ,file : UploadFile ,
                       app_settings : settings = Depends(get_settings))  :


    project_model = projectModel(
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
    

    return JSONResponse(
           content={
                "signal": ResponseSignal.FILE_UPLOADED.value,
                "file_id" : file_id             }
           )

@data_router.post("/process/{project_id}")
async def process_endpoint (request :Request ,project_id :str ,process_request : ProcessRequest) :

    file_id = process_request.file_id
    chunk_size = process_request.chunk_size
    overlap_size = process_request.overlap_size
    do_reset = process_request.Do_reset

    project_model = projectModel(
        db_client=request.app.db_client
    )

    project = await project_model.get_project_or_create_one(
        project_id=project_id
    )


    Process_Controller = processcontroller(project_id=project_id)   

    file_content = Process_Controller.get_file_content(file_id=file_id)
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
                   chunk_project_id = project.id 
                   )
                   for i,chunk in enumerate(file_chunks)
    ]

    chunk_model = ChunkModel(db_client=request.app.db_client)

    if do_reset == 1 :
        _ = await chunk_model.delete_chunk_by_project_id(project_id = project_id)



    no_records = await chunk_model.insert_many_chunks(chunks = file_chunks_records)

    return JSONResponse(
           content={
                "signal": ResponseSignal.PROCESSING_DONE.value ,
                "Inserted_chunks" : no_records   })


   


  