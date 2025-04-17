import os
import re
from dotenv import load_dotenv
from typing import List, Dict
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

# ---------- Normalization ----------
def normalize(text: str) -> str:
    return re.sub(r"\s+", "", text.lower().strip())

# ---------- College Resolver ----------
def resolve_college(input_name: str, known_colleges: List[str], alias_map: Dict[str, str]) -> str:
    input_norm = normalize(input_name)
    for full, alias in alias_map.items():
        if normalize(full) == input_norm:
            return alias
    for college in known_colleges:
        if normalize(college) == input_norm:
            return college
    return None

# ---------- Document Retriever ----------
class CollegeDocumentRetriever:
    def __init__(self, pinecone_index, top_k=5):
        self._index = pinecone_index
        self._top_k = top_k

        self.known_colleges = [
            "MIT", "Stanford", "Harvard", "UCLA", "UCSD", "UC Berkeley", "Columbia", "Gatech",
            "UWashington", "Yale", "Cornell", "CMU", "USC", "Princeton", "Georgetown",
            "University of Virginia", "BU", "EmoryUniversity", "University of Michigan",
            "Northeastern", "NEU", "NorthwesternUniversity", "NYU", "UtAustin", "UFL", "UIC", "WPI",
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
            "NEU": "Northeastern",
            "Boston University": "BU",
            "Emory University": "EmoryUniversity",
            "Tufts University": "Tufts",
            "Columbia University": "Columbia",
            "Georgia Tech": "Gatech",
            "Yale": "YaleUniv",
            "Worcester Polytechnic Institute": "WPI",
            "University of Illinois at Urbana-Champaign": "UIUC",
            "Princeton University": "Princeton",
            "Cornell University": "Cornell",
            "Northwestern University": "NorthwesternUniversity"
        }

    def get_documents_for_college(self, college: str) -> List[Document]:
        print(f"📚 Retrieving for: {college}")
        result = self._index.query(
            vector=[0.0] * 384,
            top_k=self._top_k,
            include_metadata=True,
            filter={
                "college_name": {"$eq": college},
                "type": {"$in": ["catalog", "courses"]}
            }
        )
        return [
            Document(
                page_content=m["metadata"].get("text", ""),
                metadata=m["metadata"]
            )
            for m in result.get("matches", [])
        ]

# ---------- GPT-4 Comparator ----------
class GPT4CollegeComparator:
    def __init__(self, model="gpt-4"):
        self.model = model

    def compare(self, clg1: str, clg2: str, prompt: str, college_docs: Dict[str, List[Document]]) -> str:
        context = "\n\n".join([
            f"""College: {college}
Source: {doc.metadata.get("source", "N/A")}
Text: {doc.page_content.strip()}"""
            for college, docs in college_docs.items()
            for doc in docs
        ])

        full_prompt = f"""
You are a college comparator. A student has asked to compare:

"{clg1}" and "{clg2}" on:

"{prompt}"

You have access to the following university course and catalog data:

{context if context else '[No direct content found. Please use general knowledge for a fair comparison.]'}

Please compare these two colleges thoroughly based on the above prompt.
"""

        response = openai_client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()

# ---------- CLI ----------
if __name__ == "__main__":
    retriever = CollegeDocumentRetriever(index)
    comparator = GPT4CollegeComparator()

    clg1_input = input("🏫 Enter first college name: ").strip()
    clg2_input = input("🏫 Enter second college name: ").strip()
    prompt = input("🔍 What do you want to compare them on?\n> ").strip()

    clg1 = resolve_college(clg1_input, retriever.known_colleges, retriever.alias_map)
    clg2 = resolve_college(clg2_input, retriever.known_colleges, retriever.alias_map)

    if not clg1 or not clg2:
        print("❌ Unable to resolve one or both college names. Please try again.")
        exit()

    docs1 = retriever.get_documents_for_college(clg1)
    docs2 = retriever.get_documents_for_college(clg2)

    college_docs = {clg1: docs1, clg2: docs2}

    result = comparator.compare(clg1, clg2, prompt, college_docs)
    print("\n📊 GPT-4 COMPARISON RESULT:\n")
    print(result)
