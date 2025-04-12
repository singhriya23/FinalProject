# file: retriever_only.py
import os, json
from dotenv import load_dotenv
from typing import List
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from langchain.schema import Document
from langchain.schema.retriever import BaseRetriever

load_dotenv(dotenv_path="Agents/.env")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = "college-recommendations"
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"

embedder = SentenceTransformer(EMBED_MODEL_NAME)
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)

class PineconeLangChainRetriever(BaseRetriever):
    def __init__(self, pinecone_index, top_k=4):
        super().__init__()
        self._index = pinecone_index
        self._top_k = top_k

    def get_relevant_documents(self, query: str) -> List[Document]:
        query_embedding = embedder.encode(query).tolist()
        result = self._index.query(
            vector=query_embedding,
            top_k=self._top_k,
            include_metadata=True
        )
        return [
            Document(page_content=match['metadata'].get('text', ''), metadata=match['metadata'])
            for match in result['matches']
        ]

    async def aget_relevant_documents(self, query: str) -> List[Document]:
        return self.get_relevant_documents(query)

# Just the retriever logic
retriever = PineconeLangChainRetriever(index)

def save_retriever_output(query: str, docs: List[Document], path="retriever_output.json"):
    with open(path, "w") as f:
        json.dump({
            "query": query,
            "results": [{"text": d.page_content, "metadata": d.metadata} for d in docs]
        }, f, indent=2)

if __name__ == "__main__":
    user_query = input("Enter query: ")
    docs = retriever.get_relevant_documents(user_query)
    save_retriever_output(user_query, docs)
    print(f"✅ Retrieved and saved {len(docs)} docs.")
