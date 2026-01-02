from fastapi import FastAPI
from Routes import Base
from Routes import Data
from Routes import NLP
from motor.motor_asyncio import AsyncIOMotorClient
from Helpers.Config import get_settings
from Stores.LLM.LLMProviderFactory import LLMProviderFactory
from Stores.VectorDB.VectorDBProviderFactory import VectorDBProviderFactory


app =FastAPI()

@app.on_event("startup")
async def startup_span ():
    settings = get_settings()

    app.mongo_conn = AsyncIOMotorClient(settings.MONGODB_URL)
    app.db_client = app.mongo_conn[settings.MONGODB_DATABASE]

    llm_provider_factory = LLMProviderFactory(settings)
    vectordb_provider_factory = VectorDBProviderFactory(settings)


    #Genration Client
    app.genration_client = llm_provider_factory.create(provider = settings.GENRATION_BACKEND)
    app.genration_client.set_genration_model(model_id = settings.GENRATION_MODEL_ID)


    #Embedding Client
    app.embedding_client = llm_provider_factory.create(provider = settings.EMBEDDING_BACKEND)
    app.embedding_client.set_embedding_model(model_id = settings.EMBEDDING_MODEL_ID, 
                                            embedding_size = settings.EMBEDDING_SIZE)

    #VectorDB Client
    app.vectordb_client = vectordb_provider_factory.create(provider = settings.VECTORDB_BACKEND)
    app.vectordb_client.connect()



@app.on_event("shutdown")
async def shutdown_span() :
    app.mongo_conn.close()
    app.vectordb_client.disconnect()



app.include_router(Base.base_router)
app.include_router(Data.data_router)
app.include_router(NLP.nlp_router)