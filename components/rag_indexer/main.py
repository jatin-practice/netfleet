import signal
import time

from shared.config.settings import RedisConfig, RAGConfig
from shared.transport.factory import get_transport
from shared.utils.logger import get_logger
from embedder import chunk_and_embed, load_model
from qdrant_writer import QdrantWriter, QdrantPoint, deterministic_uuid

logger = get_logger("rag_indexer")

QUEUE = RedisConfig.QUEUES["rag_raw"]
_running = True


def _handle_signal(sig, frame):
    global _running
    logger.info("Shutdown signal received — draining current batch then stopping")
    _running = False


def run() -> None:
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    logger.info("RAG Indexer starting up")

    # Load model eagerly so first messages are not slow
    load_model()

    writer = QdrantWriter()
    transport = get_transport()

    if not transport.health_check():
        logger.error("Transport health check failed — aborting startup")
        return

    logger.info(
        f"Consuming from {QUEUE} — batch_size={RAGConfig.BATCH_SIZE}"
    )

    backoff = 1

    while _running:
        try:
            messages = transport.consume_batch(
                topic=QUEUE,
                batch_size=RAGConfig.BATCH_SIZE,
                timeout=5
            )

            if not messages:
                backoff = 1
                continue

            for msg in messages:
                _index_message(msg, writer)

            backoff = 1

        except Exception as e:
            logger.error(
                f"Consumer loop error: {e} — retrying in {backoff}s"
            )
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)

    logger.info("RAG Indexer stopped")


def _index_message(msg: dict, writer: QdrantWriter) -> None:
    device_id = msg.get("device_id", "unknown")
    execution_id = msg.get("execution_id", "unknown")

    try:
        pairs = chunk_and_embed(msg["raw_output"])
        if not pairs:
            logger.debug(f"No chunks produced for device {device_id}")
            return

        points = [
            QdrantPoint(
                id=deterministic_uuid(execution_id, device_id, i),
                vector=vec,
                payload={
                    "device_id":    device_id,
                    "vendor":       msg["vendor"],
                    "region":       msg["region"],
                    "segment":      msg["segment"],
                    "operation":    msg["operation"],
                    "execution_id": execution_id,
                    "collected_at": msg["collected_at"],
                    "raw_chunk":    chunk,
                    "chunk_index":  i
                }
            )
            for i, (chunk, vec) in enumerate(pairs)
        ]

        writer.upsert_points(points)
        logger.info(
            f"Indexed {len(points)} chunks — "
            f"device={device_id} execution={execution_id}"
        )

    except Exception as e:
        # Log and skip — one bad message must not stall the consumer loop
        logger.error(
            f"Failed to index device {device_id} "
            f"(execution {execution_id}): {e}"
        )


if __name__ == "__main__":
    run()
