from enum import Enum

class VectorDBEnums (Enum) :

    QDRANT = "QDRANT"
    PGVECTOR = "PGVECTOR"


class DistanceMethodEnums (Enum) :

    COSINE = "cosine"
    DOT = "dot"
    

class PgVectorTableSchemeEnums (Enum) :
    ID = "id"
    TEXT = "text"
    VECTORS = "vectors"
    CHUNCK_ID = "chunck_id"
    METADATA = "metadata"
    _PREFIX = "pgvector"


class PgvectorDistanceMethodEnums (Enum) :
    COSINE = "vector_cosine_ops"
    DOT = "vector_12_ops"

class PgvectorIndexTypeEnums (Enum) :
    IVFFLAT = "ivfflat"
    HNSW = "hnsw"
    