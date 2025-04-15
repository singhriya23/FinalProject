import os, json
from dotenv import load_dotenv
from typing import List
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from langchain.schema import Document
from langchain.schema.retriever import BaseRetriever

# Load environment variables
load_dotenv(dotenv_path=".env")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = "college-recommendations"
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"

# Setup Pinecone and Embedder
embedder = SentenceTransformer(EMBED_MODEL_NAME)
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)

# Retriever
class PineconeLangChainRetriever(BaseRetriever):
    def __init__(self, pinecone_index, top_k=5):
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
            for match in result.get("matches", [])
        ]

    async def aget_relevant_documents(self, query: str) -> List[Document]:
        return self.get_relevant_documents(query)

# Course Recommender (Clean Output)
class CourseRecommenderAgent:
    def __init__(self, retriever: BaseRetriever):
        self.retriever = retriever

    def recommend(self, query: str) -> List[str]:
        docs = self.retriever.get_relevant_documents(query)
        if not docs:
            return ["⚠️ No matching courses found. Try refining your query."]
        return [doc.page_content for doc in docs]

    def save(self, query: str, results: List[str], path="course_recommendations.json"):
        with open(path, "w") as f:
            json.dump({"query": query, "recommendations": results}, f, indent=2)

# Run
if __name__ == "__main__":
    retriever = PineconeLangChainRetriever(index)
    agent = CourseRecommenderAgent(retriever)

    user_query = input("📘 What kind of course are you looking for (e.g., 'Machine Learning', 'Security')? ")
    results = agent.recommend(user_query)
    agent.save(user_query, results)

    print("\n📚 Course Recommendations:")
    for r in results:
        print(f"- {r}\n")
    print(f"\n✅ {len(results)} recommendations {'saved.' if results else 'returned with no match.'}")
