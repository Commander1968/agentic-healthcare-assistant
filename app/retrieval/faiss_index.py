import faiss
import numpy as np

from app.retrieval.embeddings import embed_text
from app.retrieval.knowledge_base import KNOWLEDGE_DOCUMENTS


def build_knowledge_index():
    vectors = []

    for document in KNOWLEDGE_DOCUMENTS:
        document_text = (
            f"{document['title']}\n\n"
            f"{document['content']}"
        )

        embedding = embed_text(document_text)
        vectors.append(embedding)

    matrix = np.array(vectors, dtype="float32")

    index = faiss.IndexFlatL2(matrix.shape[1])
    index.add(matrix)

    return index


def search_knowledge(query: str, top_k: int = 2):
    index = build_knowledge_index()

    query_vector = np.array(
        [embed_text(query)],
        dtype="float32"
    )

    distances, indices = index.search(
        query_vector,
        top_k
    )

    results = []

    for distance, index_position in zip(
        distances[0],
        indices[0]
    ):
        document = KNOWLEDGE_DOCUMENTS[index_position]

        results.append(
            {
                "id": document["id"],
                "title": document["title"],
                "source_name": document["source_name"],
                "source_type": document["source_type"],
                "source_url": document["source_url"],
                "content": document["content"],
                "distance": float(distance),
            }
        )

    return results