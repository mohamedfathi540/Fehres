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
    CHUNK_ID = "chunk_id"
    METADATA = "metadata"
    _PREFIX = "pgvector"


class PgvectorDistanceMethodEnums (Enum) :
    COSINE = "vector_cosine_ops"
    DOT = "vector_l2_ops"

class PgvectorIndexTypeEnums (Enum) :
    IVFFLAT = "ivfflat"
    HNSW = "hnsw"
    