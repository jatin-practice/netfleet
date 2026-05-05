import uuid
from dataclasses import dataclass
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    PayloadSchemaType,
)
from shared.config.settings import QdrantConfig
from shared.utils.logger import get_logger

logger = get_logger("rag_indexer.qdrant_writer")

# Must match the all-MiniLM-L6-v2 output dimension
VECTOR_SIZE = 384
UPSERT_BATCH_SIZE = 100


@dataclass
class QdrantPoint:
    id: str
    vector: list[float]
    payload: dict


def deterministic_uuid(
    execution_id: str,
    device_id: str,
    chunk_index: int
) -> str:
    """
    Stable UUID derived from execution + device + chunk position.
    Re-indexing the same execution overwrites existing points
    instead of creating duplicates.
    """
    key = f"{execution_id}:{device_id}:{chunk_index}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))


class QdrantWriter:
    def __init__(self):
        self._client = QdrantClient(
            host=QdrantConfig.HOST,
            port=QdrantConfig.PORT,
            timeout=10
        )
        self._collection = QdrantConfig.COLLECTION
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        existing = {
            c.name
            for c in self._client.get_collections().collections
        }
        if self._collection in existing:
            logger.info(f"Qdrant collection exists: {self._collection}")
            return

        self._client.create_collection(
            collection_name=self._collection,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE
            )
        )

        # Keyword indexes allow payload pre-filtering before vector scoring,
        # which is more efficient than post-filtering large result sets.
        for field in (
            "device_id", "vendor", "region", "segment", "operation"
        ):
            self._client.create_payload_index(
                collection_name=self._collection,
                field_name=field,
                field_schema=PayloadSchemaType.KEYWORD
            )

        self._client.create_payload_index(
            collection_name=self._collection,
            field_name="collected_at",
            field_schema=PayloadSchemaType.DATETIME
        )

        logger.info(f"Created Qdrant collection: {self._collection}")

    def upsert_points(self, points: list[QdrantPoint]) -> bool:
        if not points:
            return True
        try:
            for i in range(0, len(points), UPSERT_BATCH_SIZE):
                batch = points[i : i + UPSERT_BATCH_SIZE]
                self._client.upsert(
                    collection_name=self._collection,
                    points=[
                        PointStruct(
                            id=p.id,
                            vector=p.vector,
                            payload=p.payload
                        )
                        for p in batch
                    ]
                )
            logger.debug(
                f"Upserted {len(points)} points to {self._collection}"
            )
            return True
        except Exception as e:
            logger.error(f"Qdrant upsert failed: {e}")
            raise

    def health_check(self) -> bool:
        try:
            self._client.get_collections()
            return True
        except Exception:
            return False
