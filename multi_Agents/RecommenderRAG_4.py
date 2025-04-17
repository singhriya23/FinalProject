import os
import json
import re
from dotenv import load_dotenv
from typing import List
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from langchain.schema import Document
from openai import OpenAI

# ---------- Load environment ----------
load_dotenv("Agents/.env")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = "college-recommendations"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"

# ---------- Setup ----------
embedder = SentenceTransformer(EMBED_MODEL_NAME)
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ---------- Normalization Helper ----------
def normalize(text: str) -> str:
    return re.sub(r"\s+", "", text.lower().strip())  # remove all spaces + lowercase

# ---------- College Extractor ----------
def extract_college_name(query: str, known_colleges: List[str], alias_map: dict) -> str:
    normalized_query = normalize(query)

    # Check alias map (long name → short form used in Pinecone)
    for full_name, alias in alias_map.items():
        if normalize(full_name) in normalized_query:
            return alias

    # Check known_colleges (short forms)
    for college in known_colleges:
        if normalize(college) in normalized_query:
            return college

    return None

# ---------- Retriever ----------
class PineconeRetriever:
    def __init__(self, pinecone_index, top_k=8):
        self._index = pinecone_index
        self._top_k = top_k

        self.known_colleges = [
            "MIT", "Stanford", "Harvard", "UCLA", "UCSD", "UC Berkeley", "Columbia", "Gatech",
            "UWashington", "Yale", "Cornell", "CMU", "USC", "Princeton", "Georgetown",
            "University of Virginia", "BU", "EmoryUniversity", "University of Michigan",
            "Northeastern", "NorthwesternUniversity", "NYU", "UtAustin", "UFL", "UIC", "WPI",
            "UNCC", "Upenn", "UCBerkeley", "Tufts"
        ]

        self.alias_map = {
            "Massachusetts Institute of Technology": "MIT",
            "Stanford University": "Stanford",
            "Harvard University": "Harvard",
            "University of California Los Angeles": "UCLA",
            "University of California San Diego": "UCSD",
            "University of California Berkeley": "UC Berkeley",
            "Georgia Institute of Technology": "Gatech",
            "University of Washington": "UWashington",
            "Carnegie Mellon University": "CMU",
            "University of Southern California": "USC",
            "New York University": "NYU",
            "University of Michigan": "University of Michigan",
            "University of Florida": "UFL",
            "University of Illinois Chicago": "UIC",
            "University of North Carolina Charlotte": "UNCC",
            "University of Texas at Austin": "UtAustin",
            "University of Virginia": "University of Virginia",
            "University of Pennsylvania": "Upenn",
            "Northeastern University": "Northeastern",
            "NEU":"Northeastern",
            "Boston University": "BU",
            "Emory University": "EmoryUniversity",
            "Emory": "EmoryUniversity",
            "Tufts University": "Tufts",
            "Tuft":"Tufts",
            "Columbia University": "Columbia",
            "Georgia Tech": "Gatech",
            "Georgia Institute of Technology": "Gatech",
            "University of Texas": "UtAustin",
            "university of texas": "UtAustin",
            "Yale":"YaleUniv",
            "Worcester Polytechnic Institute": "WPI",
            "Worcester":"WPI",
            "University of Illinois at Urbana-Champaign": "UIUC",
            "Princeton University": "Princeton",
            "Cornell University": "Cornell",
            "university of california berkeley": "UC Berkeley",




            "Northwestern University": "NorthwesternUniversity"
        }

    def get_relevant_documents(self, query: str) -> List[Document]:
        embedding = embedder.encode(query).tolist()
        college = extract_college_name(query, self.known_colleges, self.alias_map)

        if college:
            print(f"🎯 Filtered search for college: {college}")
            filter_metadata = {
                "college_name": {"$in": [college]},
                "type": {"$in": ["catalog", "courses"]}
            }
        else:
            print("🔍 No college match found — retrieving based on type only.")
            filter_metadata = {
                "type": {"$in": ["catalog", "courses"]}
            }

        result = self._index.query(
            vector=embedding,
            top_k=self._top_k,
            include_metadata=True,
            filter=filter_metadata
        )

        matches = result.get("matches", [])
        print("📄 Top Matched Chunks (by college):")
        for m in matches:
            print("-", m["metadata"].get("college_name", "Unknown"), ":", m["metadata"].get("source", "N/A"))

        return [
            Document(
                page_content=m["metadata"].get("text", ""),
                metadata=m["metadata"]
            )
            for m in matches
        ]

# ---------- GPT-4 Synthesizer ----------
class GPT4Recommender:
    def __init__(self, model="gpt-4"):
        self.model = model

    def recommend(self, query: str, docs: List[Document]) -> str:
        context = "\n\n".join([
            f"""College: {doc.metadata.get("college_name", "N/A")}
Source: {doc.metadata.get("source", "N/A")}
Text: {doc.page_content.strip()}"""
            for doc in docs
        ])

        prompt = f"""
You are a course recommender. A student has asked:

"{query}"

You have access to the following universities and their context:

{context}

Your job is to recommend specific courses.
If exact matches are not found, suggest similar courses from the same college.
Do not recommend courses from other colleges unless explicitly asked.
If the user asks about admission requirements, answer based on context and general knowledge.
Be helpful, focused, and relevant to the specified university only.
"""

        response = openai_client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()

# ---------- RAG Agent ----------
class CourseRecommenderAgent:
    def __init__(self, retriever: PineconeRetriever, gpt4: GPT4Recommender):
        self.retriever = retriever
        self.gpt4 = gpt4

    def recommend(self, query: str) -> str:
        allowed_keywords = ["cs", "computer science", "data science", "ds", "ai", "artificial intelligence","CS","DS","Data Science","Data science","data Science","AI","Artificial Intelligence","artificial Intelligence","Computer Science"]
        query_lower = query.lower()

        if not any(keyword in query_lower for keyword in allowed_keywords):
            return ""

        college = extract_college_name(query, self.retriever.known_colleges, self.retriever.alias_map)
        if not college:
         return ""
        
        docs = self.retriever.get_relevant_documents(query)
        return self.gpt4.recommend(query, docs)

# ---------- CLI ----------
if __name__ == "__main__":
    retriever = PineconeRetriever(index)
    gpt4 = GPT4Recommender()
    agent = CourseRecommenderAgent(retriever, gpt4)

    user_query = input("🎓 Ask your course question (e.g., 'What AI courses does New York University offer?'):\n> ")
    answer = agent.recommend(user_query)

    print("\n🧠 GPT-4 Course Recommendations:\n")
    print(answer)
