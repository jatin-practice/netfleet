from typing import Optional
from sentence_transformers import SentenceTransformer
from shared.config.settings import RAGConfig
from shared.utils.logger import get_logger

logger = get_logger("rag_indexer.embedder")

_model: Optional[SentenceTransformer] = None


def load_model() -> None:
    """Eagerly load the embedding model at startup."""
    _get_model()


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info(f"Loading embedding model: {RAGConfig.EMBEDDING_MODEL}")
        _model = SentenceTransformer(RAGConfig.EMBEDDING_MODEL)
        logger.info("Embedding model loaded")
    return _model


def chunk_and_embed(
    text: str,
    chunk_tokens: int = RAGConfig.CHUNK_TOKENS
) -> list[tuple[str, list[float]]]:
    """
    Split CLI output at line boundaries into token-bounded chunks,
    then embed each chunk.

    Returns a list of (chunk_text, embedding_vector) pairs.
    Chunks smaller than 10 tokens are discarded — avoids embedding
    whitespace-only blocks between CLI command outputs.
    """
    lines = text.splitlines()
    chunks: list[str] = []
    current_lines: list[str] = []
    current_tokens = 0

    for line in lines:
        # Approximate token count: word count * 1.3 (LLD spec)
        line_tokens = int(len(line.split()) * 1.3)

        if current_tokens + line_tokens > chunk_tokens and current_lines:
            if current_tokens >= 10:
                chunks.append("\n".join(current_lines))
            current_lines = [line]
            current_tokens = line_tokens
        else:
            current_lines.append(line)
            current_tokens += line_tokens

    if current_lines and current_tokens >= 10:
        chunks.append("\n".join(current_lines))

    if not chunks:
        return []

    model = _get_model()
    vectors = model.encode(chunks, show_progress_bar=False)
    # .tolist() converts numpy arrays to plain Python lists; handle both
    return [
        (chunk, vec.tolist() if hasattr(vec, "tolist") else vec)
        for chunk, vec in zip(chunks, vectors)
    ]
