FROM python:3.11-slim

WORKDIR /app

# Install shared package first — layer cache survives component-only changes
COPY setup.py README.md ./
COPY shared/ ./shared/
COPY plugins/ ./plugins/
RUN pip install --no-cache-dir -e .

# Component dependencies (sentence-transformers pulls torch ~1.5GB; separate layer)
COPY components/rag_indexer/requirements.txt /tmp/rag_requirements.txt
RUN pip install --no-cache-dir -r /tmp/rag_requirements.txt

# Copy component source last so code changes don't bust the heavy dep layers
COPY components/rag_indexer/ ./components/rag_indexer/

# Run from component directory so `from embedder import ...` resolves locally
WORKDIR /app/components/rag_indexer

CMD ["python", "main.py"]
