from fastapi import FastAPI
from Routes import Base
from Routes import Data
from Routes import NLP
from Helpers.Config import get_settings
from Stores.LLM.LLMProviderFactory import LLMProviderFactory
from Stores.VectorDB.VectorDBProviderFactory import VectorDBProviderFactory
from Stores.LLM.Templates.template_parser import template_parser as TemplateParser
from sqlalchemy.ext.asyncio import create_async_engine ,AsyncSession
from sqlalchemy.orm import sessionmaker
from Utils.metrics import setup_metrics


#Create FastAPI instance
app =FastAPI()

#Setup metrics
setup_metrics(app)

#Startup event
@app.on_event("startup")
async def startup_span ():
    settings = get_settings()

    postgres_connection = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_MAIN_DB}"
    app.db_engine = create_async_engine(postgres_connection)
    app.db_client = sessionmaker(app.db_engine ,
                                class_ = AsyncSession,
                                expire_on_commit = False,
                                )

    #LLM Provider Factory 
    llm_provider_factory = LLMProviderFactory(settings)
    vectordb_provider_factory = VectorDBProviderFactory(config = settings, db_client = app.db_client)


    #Genration Client
    app.genration_client = llm_provider_factory.create(provider = settings.GENRATION_BACKEND)
    app.genration_client.set_genration_model(model_id = settings.GENRATION_MODEL_ID)


    #Embedding Client
    app.embedding_client = llm_provider_factory.create(provider = settings.EMBEDDING_BACKEND)
    app.embedding_client.set_embedding_model(model_id = settings.EMBEDDING_MODEL_ID, 
                                            embedding_size = settings.EMBEDDING_SIZE)

    #VectorDB Client
    app.vectordb_client = vectordb_provider_factory.create(provider = settings.VECTORDB_BACKEND)
    await app.vectordb_client.connect()

    #Template Parser
    app.template_parser = TemplateParser(language = settings.PRIMARY_LANGUAGE , default_language = settings.DEFUALT_LANGUAGE)

 

#Shutdown event
@app.on_event("shutdown")
async def shutdown_span() :
    await app.db_engine.dispose()
    await app.vectordb_client.disconnect()



#Include routers
app.include_router(Base.base_router)
app.include_router(Data.data_router)
app.include_router(NLP.nlp_router)