from fastapi import FastAPI
from Routes import Base
from Routes import Data


app =FastAPI()
app.include_router(Base.base_router)
app.include_router(Data.data_router)
