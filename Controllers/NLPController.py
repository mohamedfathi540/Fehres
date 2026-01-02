from .BaseController import basecontroller
from .ProjectController import projectcontroller
from fastapi import UploadFile
from Models import ResponseSignal
import re
import os



class NLPController (basecontroller) : 

    def __init__(self ,genration_client ,embedding_client ,vectordb_client) :
        super().__init__()