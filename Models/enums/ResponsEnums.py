from enum import Enum


class ResponseSignal (Enum) :


    FILE_VALIDATED = "File Validated"
    FILE_TYPE_NOT_SUPPORTED = "File Type is not Supported"
    FILE_SIZE_EXCEEDED = "File Size Ecxeeded"
    FILE_UPLOADED = "File Uploaded"
    FILE_NOT_UPLOADED = "File is not Uploaded"
    PROCESSING_DONE = "Processing Done"
    PROCESSING_FAILED = "Processing Failed"
    NO_FILE_ERROR = "files not found"
    FILE_ID_ERROR = "no file found with this id"
    