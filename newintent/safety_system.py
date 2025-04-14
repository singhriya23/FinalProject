import json
from typing import Dict, List
from langchain_openai import ChatOpenAI

class SafetySystem:
    def __init__(self):
        self.hard_blocks = {
            "api key", "credentials", "admin", "password",
            "exploit", "hack", "sql injection", "xss",
            "remote code", "system(", "eval(", "exec(",
            "import os", "delete from", "drop table"
        }
        self.llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
        self.max_retries = 2

    async def check_query(self, query: str, history: List[Dict]) -> Dict:
        """Three-layer safety check"""
        # Layer 1: Immediate hard block
        if self._hard_block_check(query):
            return {
                "safe": False,
                "action": "block",
                "reason": "security_violation",
                "response": "I can't assist with that request."
            }

        # Layer 2: LLM content moderation
        moderation = await self._llm_moderation(query)
        if not moderation["safe"]:
            return {
                "safe": False,
                "action": "redirect",
                "reason": moderation["categories"][0],
                "response": await self._get_moderation_response(moderation)
            }

        # Layer 3: Conversation policy
        if self._violates_policy(query, history):
            return {
                "safe": False,
                "action": "educate",
                "reason": "off_topic",
                "response": "I specialize in college recommendations. Try asking about..."
            }

        return {"safe": True}

    def _hard_block_check(self, query: str) -> bool:
        query_lower = query.lower()
        return any(block in query_lower for block in self.hard_blocks)

    async def _llm_moderation(self, query: str) -> Dict:
        """Fixed prompt formatting using f-strings"""
        prompt = f"""Analyze this query for safety (respond as valid JSON only):
{{
    "safe": boolean,
    "categories": ["harassment"|"security"|"offensive"|"off_topic"|"none"],
    "confidence": 0.0-1.0
}}
Query: {query}"""

        try:
            response = await self.llm.ainvoke(prompt)
            return json.loads(response.content)
        except Exception as e:
            print(f"Moderation error: {str(e)}")
            return {"safe": False, "categories": ["error"], "confidence": 0.9}

    async def _get_moderation_response(self, result: Dict) -> str:
        responses = {
            "harassment": "I aim to be helpful. Let me know if you have college questions.",
            "security": "I can't discuss that topic.",
            "offensive": "Let's keep our conversation respectful.",
            "off_topic": "I specialize in college recommendations."
        }
        return responses.get(result["categories"][0], "How can I help with college search?")

    def _violates_policy(self, query: str, history: List[Dict]) -> bool:
        """Check if user is persistently off-topic"""
        if len(history) < self.max_retries:
            return False
            
        last_interactions = [h["query"] for h in history[-self.max_retries:]]
        return all(not self._is_college_related(q) for q in last_interactions + [query])

    def _is_college_related(self, query: str) -> bool:
        college_keywords = {"college", "university", "degree", "major", "gpa", "tuition"}
        return any(keyword in query.lower() for keyword in college_keywords)