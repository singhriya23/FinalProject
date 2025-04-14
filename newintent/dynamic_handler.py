from langchain_openai import ChatOpenAI
from typing import List, Dict

class DynamicIntentHandler:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3)
        self.examples = [
            "Find colleges with strong CS programs",
            "Suggest universities for 3.5 GPA students",
            "Compare tuition between public and private schools"
        ]

    async def handle_unknown(self, query: str, history: List[Dict]) -> str:
        prompt = self._build_prompt(query, history)
        response = await self.llm.ainvoke(prompt)
        return response.content

    def _build_prompt(self, query: str, history: List[Dict]) -> str:
        return f"""You're a college advisor. Handle this unexpected query:
        
        Previous conversation:
        {self._format_history(history)}
        
        New query: {query}
        
        Respond by:
        1. Brief acknowledgment (5 words max)
        2. Gentle redirection
        3. Suggest 2-3 college-related questions
        
        Examples: {', '.join(self.examples)}
        
        Keep response under 75 words."""

    def _format_history(self, history: List[Dict]) -> str:
        return "\n".join([
            f"User: {h['query']}\nAI: {h['response']}" 
            for h in history[-3:]
        ])