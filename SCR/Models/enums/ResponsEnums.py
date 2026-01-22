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
    PROJECT_NOT_FOUND = "project not found"
    INSERT_INTO_VECTOR_DB_ERROR = "Insert into vector db error"
    INSERT_INTO_VECTOR_DB_DONE = "Inserting into vector db done"
    GET_VECTOR_COLLECTION_INFO_DONE = "Get vector collection info done"
    SEARCH_INDEX_DONE = "Search index done"
    SEARCH_INDEX_NOT_FOUND = "Search index not found"
    ANSWER_INDEX_ERROR = "Answer index error"
    ANSWER_INDEX_DONE = "Answer index done"