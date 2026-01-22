from .BaseController import basecontroller
from .ProjectController import projectcontroller
from fastapi import UploadFile
from Models import ResponseSignal
import re
import os


class datacontroller(basecontroller) :
    def __init__(self) :
        super().__init__()
        self.size_scale = 1048576 # convert MB to bytes

    def validate_uploaded_file(self, file : UploadFile) :

        if file.content_type not in self.app_settings.FILE_ALLOWED_TYPES :
            return False,ResponseSignal.FILE_TYPE_NOT_SUPPORTED.value
        
        if file.size > self.app_settings.FILE_MAX_SIZE * self.size_scale :
            return False,ResponseSignal.FILE_SIZE_EXCEEDED.value
        
        return True,ResponseSignal.FILE_UPLOADED.value
    
    def genrate_unique_filepath (self , org_filename :str ,project_id :str ) :

        random_key= self.generate_random_string()
        project_path = projectcontroller().get_project_path(project_id = project_id)

        clean_filename = self.get_clean_filename(org_filename = org_filename)

        new_file_path = os.path.join(project_path, random_key + "_" + clean_filename)

        while os.path.exists(new_file_path) :
            random_key= self.generate_random_string()
            new_file_path = os.path.join(project_path, random_key + "_" + clean_filename)
        
        return new_file_path ,random_key + "_" + clean_filename

    def get_clean_filename (self , org_filename :str ) :
        clean_filename = re.sub(r'[^\w.]' , '' , org_filename.strip())


        clean_filename = clean_filename.replace(" " ,"_")

        return clean_filename