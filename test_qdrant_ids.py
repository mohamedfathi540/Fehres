from qdrant_client import models, QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
import logging

# Mock logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_qdrant_insert():
    print("Initializing Qdrant Memory Client...")
    client = QdrantClient(":memory:")
    collection_name = "test_collection"
    
    print("Creating collection...")
    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(size=4, distance=models.Distance.COSINE)
    )
    
    # 1. Test inserting with None ID (expect failure)
    print("\nTest 1: Inserting with None ID...")
    try:
        client.upload_records(
            collection_name=collection_name,
            records=[
                models.Record(
                    id=None,
                    vector=[0.1, 0.2, 0.3, 0.4],
                    payload={"text": "test"}
                )
            ]
        )
        print("FAILURE: Insert with None ID succeeded (Unexpected).")
    except Exception as e:
        print(f"SUCCESS: Insert with None ID failed as expected. Error: {e}")

    # 2. Test inserting with 24-char ObjectId string (expect failure?)
    oid_str = "507f1f77bcf86cd799439011"
    print(f"\nTest 2: Inserting with 24-char ObjectId string '{oid_str}'...")
    try:
        client.upload_records(
            collection_name=collection_name,
            records=[
                models.Record(
                    id=oid_str,
                    vector=[0.1, 0.2, 0.3, 0.4],
                    payload={"text": "test"}
                )
            ]
        )
        print("SUCCESS: Insert with ObjectId string succeeded.")
    except Exception as e:
        print(f"FAILURE: Insert with ObjectId string failed. Error: {e}")

    # 3. Test inserting with Padded ObjectId (32-char) (expect success)
    padded_oid = oid_str + "0"*8
    print(f"\nTest 3: Inserting with Padded ObjectId string '{padded_oid}'...")
    try:
        client.upload_records(
            collection_name=collection_name,
            records=[
                models.Record(
                    id=padded_oid,
                    vector=[0.1, 0.2, 0.3, 0.4],
                    payload={"text": "test"}
                )
            ]
        )
        print("SUCCESS: Insert with Padded ObjectId string succeeded.")
    except Exception as e:
        print(f"FAILURE: Insert with Padded ObjectId string failed. Error: {e}")

if __name__ == "__main__":
    test_qdrant_insert()
