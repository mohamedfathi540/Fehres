from fastapi import FastAPI, APIRouter, Depends, UploadFile, status, Request, Query, BackgroundTasks
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
import asyncio
import os
import json
import re
import time
import threading
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


def _save_scrape_cache(
    base_url: str,
    project_id: int,
    asset_id: int,
    scraped_pages: list | None = None,
    **extra_fields,
) -> None:
    """Persist scrape cache data for resume or post-processing."""
    try:
        path = _scrape_cache_path(base_url)
        payload = {
            "base_url": base_url,
            "project_id": project_id,
            "asset_id": asset_id,
            "updated_at": time.time(),
        }
        if scraped_pages is not None:
            payload["scraped_pages"] = scraped_pages
        payload.update(extra_fields)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        logger.info(f"[SCRAPE] Cache written: {path}")
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


def _delete_scrape_cache(base_url: str) -> None:
    try:
        path = _scrape_cache_path(base_url)
        if path.exists():
            path.unlink()
            logger.info(f"[SCRAPE] Cache deleted: {path}")
    except Exception as e:
        logger.warning(f"Failed to delete scrape cache for {base_url}: {e}")


def _cache_fields(cache: dict) -> dict:
    return {
        k: v for k, v in cache.items()
        if k not in {"base_url", "project_id", "asset_id"}
    }


data_router = APIRouter(
    prefix = "/api/v1/data",
    tags = ["api_v1","data"]

)

@data_router.get("/libraries")
async def get_libraries(request: Request):
    """List all available libraries (projects)."""
    project_model = await projectModel.create_instance(db_client=request.app.db_client)
    # Get all projects - assuming a reasonable number, or we can paginate if needed.
    # For now fetching first 100 which should correspond to "libraries"
    projects, _ = await project_model.get_all_projects(page=1, page_size=100)
    
    return JSONResponse(
        content={
            "signal": ResponseSignal.SUCCESS.value if hasattr(ResponseSignal, 'SUCCESS') else "success",
            "libraries": [
                {"id": p.project_id, "name": p.project_name} 
                for p in projects
            ]
        }
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

        # Insert chunks and get their IDs
        inserted_chunk_ids = await chunk_model.insert_many_chunks_returning_ids(chunks = file_chunks_records)
        no_records += len(inserted_chunk_ids)
        no_files += 1
        
        # Trigger Embedding
        if inserted_chunk_ids:
             is_inserted, error_msg = await nlp_controller.index_into_vector_db(
                project=project,
                chunks=file_chunks_records,
                chunks_ids=inserted_chunk_ids,
                do_reset=False
             )
             if not is_inserted:
                 logger.error(f"Failed to index file {file_id}: {error_msg}")

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


async def run_scraping_background(scrape_request: ScrapeRequest, app: FastAPI):
    """Background task to run the scraping process."""
    try:
        settings = get_settings()
        library_name = scrape_request.library_name
        
        logger.info(f"[SCRAPE] Background task started for library '{library_name}'")
        
        project_model = await projectModel.create_instance(db_client=app.db_client)
        try:
            project = await project_model.get_project_or_create_one(project_name=library_name)
        except Exception as e:
            logger.error(f"[SCRAPE] Failed to get/create project in background task: {e}")
            return

        scraping_controller = ScrapingController()
        process_controller = processcontroller(project_id=project.project_id)
        chunk_model = await ChunkModel.create_instance(db_client=app.db_client)
        asset_model = await AssetModel.create_instance(db_client=app.db_client)

        do_reset = scrape_request.Do_reset
        base_url = scrape_request.base_url.strip()

        # Reset if requested
        if do_reset == 1:
            nlp_controller = NLPController(
                genration_client=app.genration_client,
                embedding_client=app.embedding_client,
                vectordb_client=app.vectordb_client,
                template_parser=app.template_parser
            )
            collection_name = nlp_controller.create_collection_name(project_id=project.project_id)
            _ = await app.vectordb_client.delete_collection(collection_name=collection_name)
            _ = await chunk_model.delete_chunk_by_project_id(project_id=project.project_id)
            try:
                from Stores.Sparse import BM25Index
                BM25Index.delete_index(project.project_id)
            except Exception:
                pass
            _delete_scrape_cache(base_url)

        cache = _load_scrape_cache(base_url) if do_reset != 1 else None

        asset_record = None
        if cache and cache.get("project_id") == project.project_id:
            asset_id = cache.get("asset_id")
            if asset_id:
                asset_record = await asset_model.get_asset_by_id(asset_id)

        if not asset_record:
            asset_resource = Asset(
                asset_project_id=project.project_id,
                asset_type=assettypeEnum.URL.value,
                asset_name=base_url,
                asset_size=0
            )
            asset_record = await asset_model.create_asset(asset=asset_resource)
            if cache and cache.get("project_id") == project.project_id:
                cache["asset_id"] = asset_record.asset_id

        if cache is None:
            cache = {
                "base_url": base_url,
                "project_id": project.project_id,
                "asset_id": asset_record.asset_id,
                "discovered_urls": [],
                "processed_urls": [],
                "skipped_urls": [],
                "pending_embedding_chunk_ids": [],
                "status": "in_progress",
            }

        # Cancel flag shared with POST /scrape-cancel so the loop can be stopped
        # We access app.state.scrape_cancel directly
        cancel_ref = {"requested": False}
        app.state.scrape_cancel = cancel_ref

        nlp_controller = NLPController(
            genration_client=app.genration_client,
            embedding_client=app.embedding_client,
            vectordb_client=app.vectordb_client,
            template_parser=app.template_parser
        )

        embed_during = bool(getattr(settings, "SCRAPING_EMBED_DURING", False))
        embed_batch_size = max(1, int(getattr(settings, "SCRAPING_EMBED_BATCH_SIZE", 50)))

        async def _embed_chunks(chunks: list, chunk_ids: list) -> bool:
            if not chunks or not chunk_ids:
                return True
            is_inserted, _ = await nlp_controller.index_into_vector_db(
                project=project, chunks=chunks, chunks_ids=chunk_ids
            )
            return is_inserted

        async def _embed_chunks_by_ids(chunk_ids: list) -> bool:
            if not chunk_ids:
                return True
            for i in range(0, len(chunk_ids), embed_batch_size):
                batch_ids = chunk_ids[i:i+embed_batch_size]
                chunks = await chunk_model.get_chunks_by_ids(chunk_ids=batch_ids)
                ok = await _embed_chunks(chunks=chunks, chunk_ids=batch_ids)
                if not ok:
                    return False
            return True

        async def _index_project_chunks() -> tuple[bool, int]:
            inserted = 0
            page_no = 1
            while True:
                page_chunks = await chunk_model.get_project_chunks(
                    project_id=project.project_id,
                    page_no=page_no,
                    page_size=500,
                )
                if not page_chunks:
                    break
                chunks_ids = [chunk.chunk_id for chunk in page_chunks]
                is_inserted, error_msg = await nlp_controller.index_into_vector_db(
                    project=project,
                    chunks=page_chunks,
                    chunks_ids=chunks_ids,
                )
                if not is_inserted:
                    logger.error(f"Failed to index project chunks: {error_msg}")
                    return False, inserted
                inserted += len(chunks_ids)
                page_no += 1
            return True, inserted

        # Ensure we have a discovered URL list
        if not cache.get("discovered_urls"):
            try:
                discovered_urls = await run_in_threadpool(
                    scraping_controller.discover_pages,
                    base_url,
                )
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                logger.error(f"Error discovering pages: {e}\n{tb}")
                return # Stop processing
            
            cache["discovered_urls"] = discovered_urls
            _save_scrape_cache(
                base_url,
                project.project_id,
                asset_record.asset_id,
                **_cache_fields(cache),
            )
        else:
            discovered_urls = cache.get("discovered_urls", [])

        if not discovered_urls:
            logger.error(f"No pages were discovered from {base_url}.")
            return

        processed_urls = set(cache.get("processed_urls", []))
        skipped_urls = set(cache.get("skipped_urls", []))
        pending_embedding_chunk_ids = list(cache.get("pending_embedding_chunk_ids", []))

        # Resume any pending embedding from a previous run
        if embed_during and pending_embedding_chunk_ids:
            ok = await _embed_chunks_by_ids(chunk_ids=pending_embedding_chunk_ids)
            if not ok:
                logger.error("Embedding failed while resuming pending chunks.")
                return
            pending_embedding_chunk_ids = []
            cache["pending_embedding_chunk_ids"] = []
            _save_scrape_cache(
                base_url,
                project.project_id,
                asset_record.asset_id,
                **_cache_fields(cache),
            )
        elif not embed_during:
            pending_embedding_chunk_ids = []
            cache["pending_embedding_chunk_ids"] = []

        remaining_urls = [
            url for url in discovered_urls
            if url not in processed_urls and url not in skipped_urls
        ]

        if not remaining_urls:
            logger.info("No remaining URLs to process.")
            return

        concurrency = max(1, int(getattr(settings, "SCRAPING_CONCURRENCY", 1)))
        if getattr(settings, "SCRAPING_USE_BROWSER", False):
            concurrency = 1

        rate_limiter = {"lock": threading.Lock(), "last_time": 0.0}
        rate_limit_seconds = getattr(settings, "SCRAPING_RATE_LIMIT", 0.0)

        def _scrape_page_sync(url: str, log_debug_first: bool):
            if rate_limit_seconds and rate_limit_seconds > 0:
                with rate_limiter["lock"]:
                    now = time.time()
                    elapsed = now - rate_limiter["last_time"]
                    wait = rate_limit_seconds - elapsed
                    if wait > 0:
                        time.sleep(wait)
                    rate_limiter["last_time"] = time.time()
            controller = scraping_controller if concurrency == 1 else ScrapingController()
            return controller.scrape_page(url, log_debug_first=log_debug_first)

        async def _process_page_data(page_data: dict):
            nonlocal pending_embedding_chunk_ids, cache
            html_content = page_data["content"]
            url = page_data["url"]
            metadata = page_data.get("metadata", {})

            file_chunks = await run_in_threadpool(
                process_controller.process_html_content,
                html_content=html_content,
                url=url,
                chunk_size=settings.DOC_CHUNK_SIZE,
                overlap_size=settings.DOC_OVERLAP_SIZE
            )

            if not file_chunks:
                processed_urls.add(url)
                cache["processed_urls"] = list(processed_urls)
                _save_scrape_cache(
                    base_url,
                    project.project_id,
                    asset_record.asset_id,
                    **_cache_fields(cache),
                )
                return 0, [], []

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

            inserted_ids = await chunk_model.insert_many_chunks_returning_ids(
                chunks=file_chunks_records
            )
            if embed_during and inserted_ids:
                pending_embedding_chunk_ids.extend(inserted_ids)
            processed_urls.add(url)
            cache["processed_urls"] = list(processed_urls)
            if embed_during:
                cache["pending_embedding_chunk_ids"] = pending_embedding_chunk_ids
            _save_scrape_cache(
                base_url,
                project.project_id,
                asset_record.asset_id,
                **_cache_fields(cache),
            )
            return len(file_chunks_records), file_chunks_records, inserted_ids

        async def _flush_embed_buffer(embed_buffer_chunks: list, embed_buffer_ids: list):
            nonlocal pending_embedding_chunk_ids, cache
            while len(embed_buffer_ids) >= embed_batch_size:
                batch_chunks = embed_buffer_chunks[:embed_batch_size]
                batch_ids = embed_buffer_ids[:embed_batch_size]
                ok = await _embed_chunks(chunks=batch_chunks, chunk_ids=batch_ids)
                if not ok:
                    return False, embed_buffer_chunks, embed_buffer_ids
                embed_buffer_chunks = embed_buffer_chunks[embed_batch_size:]
                embed_buffer_ids = embed_buffer_ids[embed_batch_size:]
                embedded_set = set(batch_ids)
                pending_embedding_chunk_ids = [
                    cid for cid in pending_embedding_chunk_ids if cid not in embedded_set
                ]
                cache["pending_embedding_chunk_ids"] = pending_embedding_chunk_ids
                _save_scrape_cache(
                    base_url,
                    project.project_id,
                    asset_record.asset_id,
                    **_cache_fields(cache),
                )
            return True, embed_buffer_chunks, embed_buffer_ids

        no_records = 0
        no_pages = 0
        skipped_count = 0
        embed_buffer_chunks = []
        embed_buffer_ids = []
        robots_parser = scraping_controller._check_robots_txt(base_url)

        async def _handle_scrape_result(result: dict):
            nonlocal no_records, no_pages, skipped_count, embed_buffer_chunks, embed_buffer_ids
            url = result.get("url")
            page_data = result.get("page_data")
            skip_reason = result.get("skip_reason")
            index = result.get("index")
            total = result.get("total")
            if cancel_ref.get("requested"):
                return False
            if not page_data:
                skipped_urls.add(url)
                skipped_count += 1
                cache["skipped_urls"] = list(skipped_urls)
                _save_scrape_cache(
                    base_url,
                    project.project_id,
                    asset_record.asset_id,
                    **_cache_fields(cache),
                )
                reason = skip_reason or "unknown"
                if index and total:
                    logger.warning(f"[SCRAPE] SKIP {index}/{total}: {url} ({reason})")
                else:
                    logger.warning(f"[SCRAPE] SKIP: {url} ({reason})")
                return True
            try:
                inserted_count, chunks, ids = await _process_page_data(page_data)
                no_pages += 1
                if inserted_count:
                    no_records += inserted_count
                    if embed_during:
                        embed_buffer_chunks.extend(chunks)
                        embed_buffer_ids.extend(ids)
                        ok, embed_buffer_chunks, embed_buffer_ids = await _flush_embed_buffer(
                            embed_buffer_chunks, embed_buffer_ids
                        )
                        if not ok:
                            return False
                if index and total:
                    logger.info(f"[SCRAPE] OK {index}/{total}: {url}")
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                logger.error(f"[SCRAPE] Error processing page {url}: {e}\n{tb}")
            return True

        if concurrency == 1:
            total = len(remaining_urls)
            try:
                for idx, url in enumerate(remaining_urls, 1):
                    if cancel_ref.get("requested"):
                        break
                    if not scraping_controller._can_fetch(robots_parser, url):
                        result = {
                            "url": url,
                            "page_data": None,
                            "skip_reason": "robots.txt disallows URL",
                            "index": idx,
                            "total": total,
                        }
                    else:
                        log_debug_first = idx == 1 and getattr(settings, "SCRAPING_DEBUG", False)
                        page_data, skip_reason = await run_in_threadpool(
                            _scrape_page_sync, url, log_debug_first
                        )
                        result = {
                            "url": url,
                            "page_data": page_data,
                            "skip_reason": skip_reason,
                            "index": idx,
                            "total": total,
                        }
                    ok = await _handle_scrape_result(result)
                    if not ok:
                        logger.error("Embedding failed during scraping.")
                        return 
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                logger.error(f"Error scraping documentation: {e}\n{tb}")
                return
        else:
            total = len(remaining_urls)

            async def _scrape_one(url: str, index: int):
                if not scraping_controller._can_fetch(robots_parser, url):
                    return {
                        "url": url,
                        "page_data": None,
                        "skip_reason": "robots.txt disallows URL",
                        "index": index,
                        "total": total,
                    }
                log_debug_first = index == 1 and getattr(settings, "SCRAPING_DEBUG", False)
                page_data, skip_reason = await run_in_threadpool(
                    _scrape_page_sync, url, log_debug_first
                )
                return {
                    "url": url,
                    "page_data": page_data,
                    "skip_reason": skip_reason,
                    "index": index,
                    "total": total,
                }

            pending_tasks = set()
            url_iter = iter(list(enumerate(remaining_urls, 1)))
            cancelled = False

            for _ in range(min(concurrency, len(remaining_urls))):
                idx, url = next(url_iter)
                pending_tasks.add(asyncio.create_task(_scrape_one(url, idx)))

            while pending_tasks:
                done, pending_tasks = await asyncio.wait(
                    pending_tasks, return_when=asyncio.FIRST_COMPLETED
                )
                for task in done:
                    result = task.result()
                    if cancel_ref.get("requested"):
                        cancelled = True
                        continue
                    ok = await _handle_scrape_result(result)
                    if not ok:
                         logger.error("Embedding failed during scraping.")
                         return
                    if not cancelled:
                        try:
                            idx, url = next(url_iter)
                            pending_tasks.add(asyncio.create_task(_scrape_one(url, idx)))
                        except StopIteration:
                            pass

        if cancel_ref.get("requested"):
            logger.info(f"Scrape cancelled for {base_url} ({no_pages} pages processed)")
            return

        if embed_during and embed_buffer_ids:
            ok = await _embed_chunks(chunks=embed_buffer_chunks, chunk_ids=embed_buffer_ids)
            if not ok:
                logger.error("Embedding failed for remaining chunks.")
                return 
            embedded_set = set(embed_buffer_ids)
            pending_embedding_chunk_ids = [
                cid for cid in pending_embedding_chunk_ids if cid not in embedded_set
            ]
            cache["pending_embedding_chunk_ids"] = pending_embedding_chunk_ids
            _save_scrape_cache(
                base_url,
                project.project_id,
                asset_record.asset_id,
                **_cache_fields(cache),
            )

        auto_indexed_chunks = 0
        if not embed_during and getattr(settings, "SCRAPING_AUTO_INDEX", True):
            ok, auto_indexed_chunks = await _index_project_chunks()
            if not ok:
                logger.error("Auto indexing failed after scraping completed.")
                return

        if (embed_during or auto_indexed_chunks > 0) and getattr(settings, "HYBRID_SEARCH_ENABLED", True):
            try:
                logger.info(f"[SCRAPE] Starting BM25 indexing for project {project.project_id}...")
                from Stores.Sparse import BM25Index
                all_chunks = []
                page_no = 1
                while True:
                    page_chunks = await chunk_model.get_project_chunks(
                        project_id=project.project_id, page_no=page_no, page_size=500
                    )
                    if not page_chunks:
                        break
                    all_chunks.extend(page_chunks)
                    page_no += 1
                
                logger.info(f"[SCRAPE] Fetched {len(all_chunks)} chunks for BM25 indexing.")
                if all_chunks:
                    BM25Index.build_index(project.project_id, all_chunks)
                    logger.info(f"[SCRAPE] BM25 indexing completed for project {project.project_id}.")
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                logger.error(f"[SCRAPE] BM25 index build failed: {e}\n{tb}")

        cache["status"] = "completed"
        _save_scrape_cache(
            base_url,
            project.project_id,
            asset_record.asset_id,
            **_cache_fields(cache),
        )
        logger.info(f"[SCRAPE] Completed for {base_url}. Pages: {no_pages}, Chunks: {no_records}")

    except Exception as e:
         logger.error(f"[SCRAPE] Fatal error in background task: {e}")


@data_router.post("/scrape")
async def scrape_documentation(
    request: Request,
    scrape_request: ScrapeRequest,
    background_tasks: BackgroundTasks
):
    """
    Scrape library documentation from a base URL (Runs in background).
    Returns immediately with ACCEPTED status.
    """
    library_name = scrape_request.library_name
    if not library_name:
         return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"signal": "LIBRARY_NAME_REQUIRED", "message": "Library Name is required"}
        )

    base_url = scrape_request.base_url.strip()
    
    # 1. Quick URL validation
    scraping_controller = ScrapingController()
    if not scraping_controller.verify_url_accessible(base_url):
         return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": "URL_NOT_ACCESSIBLE",
                "message": f"URL {base_url} is not accessible (or returned non-200). Please check."
            }
        )

    # 2. Get/Create Project to ensure we have a valid ID
    project_model = await projectModel.create_instance(db_client=request.app.db_client)
    try:
        project = await project_model.get_project_or_create_one(project_name=library_name)
    except Exception as e:
        logger.error(f"Failed to get/create project: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"signal": "PROJECT_CREATION_ERROR", "message": str(e)}
        )
    
    # 3. Queue request
    # Pass 'request.app' to the background task to access shared clients
    background_tasks.add_task(
        run_scraping_background,
        scrape_request,
        request.app
    )
    
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "signal": "SCRAPING_STARTED",
            "message": f"Scraping started in background for {library_name}",
            "project_id": project.project_id
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
    if not cache:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "signal": ResponseSignal.PROCESSING_FAILED.value,
                "error": f"No scrape cache found for {body.base_url}. Run a scrape first."
            }
        )
    if "scraped_pages" not in cache:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.PROCESSING_FAILED.value,
                "error": "Scrape cache is in streaming mode and does not contain raw pages to process."
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

