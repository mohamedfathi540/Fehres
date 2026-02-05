from fastapi import FastAPI, APIRouter, Depends, UploadFile, status, Request, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
import os
import json
import re
from pathlib import Path
from Helpers.Config import get_settings,settings
from Controllers import datacontroller ,projectcontroller ,processcontroller,NLPController
from Controllers.ScrapingController import ScrapingController
import aiofiles
from Models import ResponseSignal
import logging
from .Schemes.Date_Schemes import ProcessRequest, ScrapeRequest, ProcessScrapeCacheRequest
from Models.Project_Model import projectModel
from Models.DB_Schemes import dataChunk ,Asset
from Models.Chunk_Model import ChunkModel
from Models.Asset_Model import AssetModel
from Models.enums.AssetTypeEnum import assettypeEnum


logger = logging.getLogger("uvicorn.error")

# Directory for scrape cache (so chunking can be resumed after frontend timeout)
SCRAPE_CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "scrape_cache"


def _scrape_cache_path(base_url: str) -> Path:
    """Path to cache file for a given base_url."""
    safe = re.sub(r"^https?://", "", base_url.strip().rstrip("/"))
    safe = re.sub(r"[^\w\-.]", "_", safe)
    SCRAPE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return SCRAPE_CACHE_DIR / f"{safe}.json"


def _save_scrape_cache(base_url: str, project_id: int, asset_id: int, scraped_pages: list) -> None:
    """Persist scraped pages so chunking can be run later (e.g. after client timeout)."""
    try:
        path = _scrape_cache_path(base_url)
        payload = {
            "base_url": base_url,
            "project_id": project_id,
            "asset_id": asset_id,
            "scraped_pages": scraped_pages,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        logger.info(f"[SCRAPE] Cache written: {path} ({len(scraped_pages)} pages)")
    except Exception as e:
        logger.warning(f"Failed to write scrape cache: {e}")


def _load_scrape_cache(base_url: str) -> dict | None:
    """Load cached scrape for base_url. Returns None if missing or invalid."""
    try:
        path = _scrape_cache_path(base_url)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load scrape cache for {base_url}: {e}")
        return None


data_router = APIRouter(
    prefix = "/api/v1/data",
    tags = ["api_v1","data"]

)

@data_router.post("/upload")
async def upload_data (request :Request, file : UploadFile ,
                       app_settings : settings = Depends(get_settings))  :

    settings = get_settings()
    default_project_id = settings.DEFAULT_PROJECT_ID

    project_model = await projectModel.create_instance(
        db_client=request.app.db_client
    )

    project = await project_model.get_project_or_create_one(
        project_id=default_project_id
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
    
    project_dir_path = projectcontroller().get_project_path(project_id = default_project_id )
    file_path, file_id = data_controller.genrate_unique_filepath(org_filename=file.filename ,project_id=default_project_id )



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


@data_router.delete("/asset/{file_id}")
async def delete_asset(request: Request, file_id: str):
    """Remove an asset (and its chunks/vectors) from the project. file_id can be asset_id (integer) or asset_name (e.g. filename)."""
    settings = get_settings()
    default_project_id = settings.DEFAULT_PROJECT_ID
    
    project_model = await projectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=default_project_id)
    if not project:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"signal": ResponseSignal.PROJECT_NOT_FOUND.value},
        )
    asset_model = await AssetModel.create_instance(db_client=request.app.db_client)
    chunk_model = await ChunkModel.create_instance(db_client=request.app.db_client)
    try:
        asset_id_int = int(file_id)
        asset = await asset_model.get_asset_by_id(asset_id=asset_id_int)
    except ValueError:
        asset = await asset_model.get_asset_record(
            asset_project_id=project.project_id, asset_name=file_id
        )
    if not asset or asset.asset_project_id != project.project_id:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"signal": ResponseSignal.ASSET_NOT_FOUND.value},
        )
    asset_id = asset.asset_id
    chunk_ids = await chunk_model.get_chunk_ids_by_asset_id(asset_id)
    if chunk_ids:
        nlp_controller = NLPController(
            genration_client=request.app.genration_client,
            embedding_client=request.app.embedding_client,
            vectordb_client=request.app.vectordb_client,
            template_parser=request.app.template_parser,
        )
        collection_name = nlp_controller.create_collection_name(project_id=project.project_id)
        await request.app.vectordb_client.delete_by_chunk_ids(collection_name, chunk_ids)
    await chunk_model.delete_chunks_by_asset_id(asset_id)
    await asset_model.delete_asset(asset_id)
    return JSONResponse(
        content={"signal": ResponseSignal.ASSET_DELETED.value, "asset_id": asset_id},
    )


@data_router.delete("/assets")
async def delete_all_assets(request: Request):
    """Remove all file assets (and their chunks/vectors) from the project."""
    settings = get_settings()
    default_project_id = settings.DEFAULT_PROJECT_ID
    
    project_model = await projectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=default_project_id)
    if not project:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"signal": ResponseSignal.PROJECT_NOT_FOUND.value},
        )
    asset_model = await AssetModel.create_instance(db_client=request.app.db_client)
    chunk_model = await ChunkModel.create_instance(db_client=request.app.db_client)
    assets = await asset_model.get_all_project_asset(
        asset_project_id=project.project_id,
        asset_type=assettypeEnum.FILE.value,
    )
    if not assets:
        return JSONResponse(
            content={
                "signal": ResponseSignal.ASSETS_DELETED.value,
                "deleted_count": 0,
            },
        )
    nlp_controller = NLPController(
        genration_client=request.app.genration_client,
        embedding_client=request.app.embedding_client,
        vectordb_client=request.app.vectordb_client,
        template_parser=request.app.template_parser,
    )
    collection_name = nlp_controller.create_collection_name(project_id=project.project_id)
    deleted_count = 0
    for asset in assets:
        asset_id = asset.asset_id
        chunk_ids = await chunk_model.get_chunk_ids_by_asset_id(asset_id)
        if chunk_ids:
            await request.app.vectordb_client.delete_by_chunk_ids(
                collection_name, chunk_ids
            )
        await chunk_model.delete_chunks_by_asset_id(asset_id)
        await asset_model.delete_asset(asset_id)
        deleted_count += 1
    if deleted_count > 0:
        try:
            await request.app.vectordb_client.delete_collection(
                collection_name=collection_name
            )
        except Exception:
            pass
        try:
            from Stores.Sparse import BM25Index
            BM25Index.delete_index(project.project_id)
        except Exception:
            pass
    return JSONResponse(
        content={
            "signal": ResponseSignal.ASSETS_DELETED.value,
            "deleted_count": deleted_count,
        },
    )


@data_router.post("/process")
async def process_endpoint (request :Request ,process_request : ProcessRequest) :

    settings = get_settings()
    default_project_id = settings.DEFAULT_PROJECT_ID
    chunk_size = settings.DOC_CHUNK_SIZE
    overlap_size = settings.DOC_OVERLAP_SIZE
    do_reset = process_request.Do_reset

    project_model =await projectModel.create_instance(
        db_client=request.app.db_client
    )

    project = await project_model.get_project_or_create_one(
        project_id=default_project_id
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
        try:
            file_id_int = int(process_request.file_id)
            asset_record = await asset_model.get_asset_by_id(asset_id=file_id_int)
        except ValueError:
            # If it's not a numeric ID, try looking up by name (backwards compatibility)
            asset_record = await asset_model.get_asset_record(asset_project_id=default_project_id,
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


    Process_Controller = processcontroller(project_id=default_project_id)   

    no_files = 0
    no_records = 0

    chunk_model = await ChunkModel.create_instance(db_client=request.app.db_client)


    if do_reset == 1 :
        #delete associated vectors collection
        collection_name = nlp_controller.create_collection_name(project_id=project.project_id)
        _ = await request.app.vectordb_client.delete_collection(collection_name=collection_name)
        #delete associated chunks
        _ = await chunk_model.delete_chunk_by_project_id(project_id = project.project_id)
        try:
            from Stores.Sparse import BM25Index
            BM25Index.delete_index(project.project_id)
        except Exception:
            pass

    for asset_id, file_id in project_files_ids.items():
        try:
            file_content = await run_in_threadpool(Process_Controller.get_file_content, file_id=file_id)
        except Exception as e:
            err_msg = str(e)
            logger.error("Error while processing file %s: %s", file_id, err_msg)
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "signal": ResponseSignal.PROCESSING_FAILED.value,
                    "error": f"Failed to load file {file_id}. {err_msg}",
                    "hint": "PDF may be encrypted, corrupted, or unsupported; try an unprotected or re-exported copy.",
                },
            )

        if file_content is None:
            logger.error("Error while processing file: %s (file not found or not readable)", file_id)
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "signal": ResponseSignal.PROCESSING_FAILED.value,
                    "error": f"File not found or not readable: {file_id}. Check that the file exists in the project and has read permissions.",
                },
            )

        file_chunks = await run_in_threadpool(
            Process_Controller.process_file_content,
            file_content = file_content,
            file_id = file_id,
            chunk_size = chunk_size,
            overlap_size = overlap_size
            
        )

        if file_chunks is None or len(file_chunks) == 0:
            return JSONResponse(
            status_code = status.HTTP_400_BAD_REQUEST,
            content={
                    "signal": ResponseSignal.PROCESSING_FAILED.value,
                    "error": f"Processing resulted in 0 chunks for file {file_id}. Please check if the file contains readable text."
            }
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


@data_router.get("/scrape-debug")
async def scrape_debug(url: str = Query(..., description="URL to fetch and inspect")):
    """Fetch one URL and return debug info: status, content_type, html_len, extracted_len, extracted_snippet (no storage)."""
    scraping_controller = ScrapingController()
    result = await run_in_threadpool(
        scraping_controller.scrape_page_debug,
        url=url
    )
    return JSONResponse(content=result)


@data_router.post("/scrape-cancel")
async def scrape_cancel(request: Request):
    """Request to cancel the currently running scrape. No-op if no scrape is running."""
    # Set request-bound cancel flag
    cancel_ref = getattr(request.app.state, "scrape_cancel", None)
    if isinstance(cancel_ref, dict):
        cancel_ref["requested"] = True
    # Also set global cancel flag (works across restarts)
    from Controllers.ScrapingController import GLOBAL_SCRAPE_CANCEL
    GLOBAL_SCRAPE_CANCEL["requested"] = True
    logger.info("Scrape cancel requested (global + local)")
    return JSONResponse(content={"signal": "cancelled", "message": "Cancel requested"})


@data_router.post("/scrape")
async def scrape_documentation(request: Request, scrape_request: ScrapeRequest):
    """Scrape library documentation from a base URL."""
    settings = get_settings()
    default_project_id = settings.DEFAULT_PROJECT_ID
    
    project_model = await projectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=default_project_id)
    
    if not project:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"signal": ResponseSignal.PROJECT_NOT_FOUND.value}
        )
    
    scraping_controller = ScrapingController()
    process_controller = processcontroller(project_id=default_project_id)
    chunk_model = await ChunkModel.create_instance(db_client=request.app.db_client)
    asset_model = await AssetModel.create_instance(db_client=request.app.db_client)
    
    do_reset = scrape_request.Do_reset
    
    # Create asset for the URL
    asset_resource = Asset(
        asset_project_id=project.project_id,
        asset_type=assettypeEnum.URL.value,
        asset_name=scrape_request.base_url,
        asset_size=0
    )
    asset_record = await asset_model.create_asset(asset=asset_resource)
    
    # Reset if requested
    if do_reset == 1:
        nlp_controller = NLPController(
            genration_client=request.app.genration_client,
            embedding_client=request.app.embedding_client,
            vectordb_client=request.app.vectordb_client,
            template_parser=request.app.template_parser
        )
        collection_name = nlp_controller.create_collection_name(project_id=project.project_id)
        _ = await request.app.vectordb_client.delete_collection(collection_name=collection_name)
        _ = await chunk_model.delete_chunk_by_project_id(project_id=project.project_id)
        try:
            from Stores.Sparse import BM25Index
            BM25Index.delete_index(project.project_id)
        except Exception:
            pass
    
    # Cancel flag shared with POST /scrape-cancel so the loop can be stopped
    cancel_ref = {"requested": False}
    request.app.state.scrape_cancel = cancel_ref

    # Scrape documentation
    try:
        scraped_pages = await run_in_threadpool(
            scraping_controller.scrape_documentation,
            scrape_request.base_url,
            cancel_ref,
        )
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Error scraping documentation: {e}\n{tb}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "signal": ResponseSignal.PROCESSING_FAILED.value,
                "error": f"Scraping failed: {str(e)}"
            }
        )

    # Cancelled by user: do not save cache or process; return so client can stop pending state
    if cancel_ref.get("requested"):
        logger.info(f"Scrape cancelled for {scrape_request.base_url} ({len(scraped_pages)} pages scraped)")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "signal": "cancelled",
                "message": "Scrape cancelled",
                "partial_pages_scraped": len(scraped_pages),
            },
        )
    
    if not scraped_pages:
        logger.warning(f"Scraping returned 0 pages for URL: {scrape_request.base_url}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.PROCESSING_FAILED.value,
                "error": f"No pages were successfully scraped from {scrape_request.base_url}. "
                         f"Check that the URL is reachable and contains HTML documentation."
            }
        )
    
    # Save cache so chunking can be resumed via POST /data/process-scrape-cache if client times out
    _save_scrape_cache(
        scrape_request.base_url,
        project.project_id,
        asset_record.asset_id,
        scraped_pages,
    )
    
    # Process each page into chunks
    no_records = 0
    no_pages = 0
    
    for page_data in scraped_pages:
        try:
            html_content = page_data['content']
            url = page_data['url']
            metadata = page_data.get('metadata', {})
            
            file_chunks = await run_in_threadpool(
                process_controller.process_html_content,
                html_content=html_content,
                url=url,
                chunk_size=settings.DOC_CHUNK_SIZE,
                overlap_size=settings.DOC_OVERLAP_SIZE
            )
            
            if file_chunks and len(file_chunks) > 0:
                # Merge metadata
                for chunk in file_chunks:
                    chunk.metadata.update(metadata)
                
                file_chunks_records = [
                    dataChunk(
                        chunk_text=chunk.page_content,
                        chunk_metadata=chunk.metadata,
                        chunk_order=i+1,
                        chunk_project_id=project.project_id,
                        chunk_asset_id=asset_record.asset_id
                    )
                    for i, chunk in enumerate(file_chunks)
                ]
                
                no_records += await chunk_model.insert_many_chunks(chunks=file_chunks_records)
                no_pages += 1
        except Exception as e:
            logger.error(f"Error processing page {page_data.get('url', 'unknown')}: {e}")
            continue
    
    return JSONResponse(
        content={
            "signal": ResponseSignal.PROCESSING_DONE.value,
            "Inserted_chunks": no_records,
            "processed_pages": no_pages,
            "total_pages_scraped": len(scraped_pages)
        }
    )


@data_router.post("/process-scrape-cache")
async def process_scrape_cache(request: Request, body: ProcessScrapeCacheRequest):
    """
    Run chunking (and optionally indexing) from a saved scrape cache.
    Use this after a scrape completed on the backend but the frontend timed out:
    no refetch, just process the cached HTML into chunks and DB.
    Then call POST /api/v1/nlp/index/push to embed and index.
    """
    settings = get_settings()
    cache = _load_scrape_cache(body.base_url)
    if not cache or "scraped_pages" not in cache:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "signal": ResponseSignal.PROCESSING_FAILED.value,
                "error": f"No scrape cache found for {body.base_url}. Run a scrape first; cache is written when scrape finishes."
            }
        )
    project_id = cache["project_id"]
    asset_id = cache["asset_id"]
    scraped_pages = cache["scraped_pages"]

    project_model = await projectModel.create_instance(db_client=request.app.db_client)
    asset_model = await AssetModel.create_instance(db_client=request.app.db_client)
    chunk_model = await ChunkModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)
    if not project:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"signal": ResponseSignal.PROJECT_NOT_FOUND.value}
        )
    asset = await asset_model.get_asset_by_id(asset_id)
    if not asset:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "signal": ResponseSignal.PROCESSING_FAILED.value,
                "error": f"Asset {asset_id} from cache no longer exists. Re-run the scrape."
            }
        )

    process_controller = processcontroller(project_id=project_id)
    await chunk_model.delete_chunks_by_asset_id(asset_id)

    no_records = 0
    no_pages = 0
    for page_data in scraped_pages:
        try:
            html_content = page_data["content"]
            url = page_data["url"]
            metadata = page_data.get("metadata", {})
            file_chunks = await run_in_threadpool(
                process_controller.process_html_content,
                html_content=html_content,
                url=url,
                chunk_size=settings.DOC_CHUNK_SIZE,
                overlap_size=settings.DOC_OVERLAP_SIZE,
            )
            if file_chunks and len(file_chunks) > 0:
                for chunk in file_chunks:
                    chunk.metadata.update(metadata)
                file_chunks_records = [
                    dataChunk(
                        chunk_text=chunk.page_content,
                        chunk_metadata=chunk.metadata,
                        chunk_order=i + 1,
                        chunk_project_id=project.project_id,
                        chunk_asset_id=asset_id,
                    )
                    for i, chunk in enumerate(file_chunks)
                ]
                no_records += await chunk_model.insert_many_chunks(chunks=file_chunks_records)
                no_pages += 1
        except Exception as e:
            logger.error(f"Error processing page {page_data.get('url', 'unknown')}: {e}")
            continue

    return JSONResponse(
        content={
            "signal": ResponseSignal.PROCESSING_DONE.value,
            "Inserted_chunks": no_records,
            "processed_pages": no_pages,
            "total_pages_scraped": len(scraped_pages)
        }
    )

