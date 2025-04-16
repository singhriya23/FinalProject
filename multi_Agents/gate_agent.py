import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional
from newintent.dynamic_handler import DynamicIntentHandler
from newintent.safety_system import SafetySystem
from sentence_transformers import SentenceTransformer, util

# Setup logging
logging.basicConfig(
    level=logging.INFO,  # Switch to INFO to reduce logging noise
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CollegeRecommender:
    def __init__(self):
        self.safety_system = SafetySystem()
        self.dynamic_handler = DynamicIntentHandler()
        self.conversation_history: List[Dict] = []
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.college_examples = [
            "Which universities offer data science in California?",
            "What's the tuition fee for Stanford?",
            "Suggest affordable engineering colleges",
            "I have a 3.8 GPA, what colleges can I get into?",
            "Best colleges for computer science in the US"
        ]
        self.college_embeddings = self.model.encode(self.college_examples, convert_to_tensor=True)

    async def handle_query(self, query: str) -> Dict:
        logger.info(f"Query: {query}")
        classification = await self.check_and_classify_query(query)
        logger.info(f"College-related: {classification['is_college_related']}")

        if classification["context"] == "college":
            response = await self._handle_college_query(query)
            self._update_history(query, response, "college_response")
            return self._build_response(response)

        return self._build_response(
            classification["response"],
            {"context": classification["context"]}
        )

    async def _handle_college_query(self, query: str) -> str:
        mock_responses = {
            "tuition": "Average tuition is $35,000/year for private colleges.",
            "engineering": "Top engineering schools: MIT, Stanford, UC Berkeley",
            "gpa": "For 3.5+ GPA students, consider these reach schools...",
        }

        query_lower = query.lower()
        for keyword, response in mock_responses.items():
            if keyword in query_lower:
                return response

        return await self.dynamic_handler.handle_unknown(
            query,
            self.conversation_history
        )

    def _is_college_related(self, query: str) -> bool:
        query_embedding = self.model.encode(query, convert_to_tensor=True)
        similarity_scores = util.cos_sim(query_embedding, self.college_embeddings)
        max_score = float(similarity_scores.max())
        logger.debug(f"Max semantic similarity score: {max_score}")
        return max_score > 0.5

    def _update_history(self, query: str, response: str, context: str):
        self.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "response": response,
            "context": context,
            "turns": len(self.conversation_history) + 1
        })

        if len(self.conversation_history) > 20:
            self.conversation_history.pop(0)

    def _build_response(self, message: str, metadata: Optional[Dict] = None) -> Dict:
        return {
            "response": message,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }

    async def check_and_classify_query(self, query: str) -> Dict:
        if not query.strip():
            return {
                "is_college_related": False,
                "safety_check_passed": False,
                "response": "Please enter a valid question.",
                "context": "error"
            }

        try:
            safety_result = await self.safety_system.check_query(query, self.conversation_history)
            if not safety_result["safe"]:
                self._update_history(query, safety_result["response"], "safety_block")
                return {
                    "is_college_related": False,
                    "safety_check_passed": False,
                    "response": safety_result["response"],
                    "context": "safety_block"
                }
        except Exception:
            return {
                "is_college_related": False,
                "safety_check_passed": False,
                "response": "Error during safety check",
                "context": "error"
            }

        try:
            is_college = self._is_college_related(query)
            if not is_college:
                general_response = await self.dynamic_handler.handle_unknown(query, self.conversation_history)
                self._update_history(query, general_response, "general")
                return {
                    "is_college_related": False,
                    "safety_check_passed": True,
                    "response": general_response,
                    "context": "general"
                }

            return {
                "is_college_related": True,
                "safety_check_passed": True,
                "context": "college"
            }

        except Exception:
            return {
                "is_college_related": False,
                "safety_check_passed": False,
                "response": "Error during query classification",
                "context": "error"
            }


async def interactive_demo():
    agent = CollegeRecommender()
    print("College Recommendation Assistant (type 'quit' to exit)\n")

    while True:
        try:
            query = input("You: ")
            if query.lower() in {'quit', 'exit'}:
                break

            response = await agent.handle_query(query)
            print(f"Assistant: {response['response']}\n")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    asyncio.run(interactive_demo())
