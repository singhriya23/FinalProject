from typing import Dict, List
import asyncio
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

class WebSearchRecommender:
    def __init__(self):
        self.search = GoogleSerperAPIWrapper(
            serper_api_key=os.getenv("SERPER_API_KEY"),
            k=7  # Get more results for GPT to analyze
        )
        self.llm = ChatOpenAI(model="gpt-4-turbo")  # Using more capable model

    async def recommend(self, query: str) -> Dict:
        """End-to-end recommendation with minimal processing"""
        # Get raw search results
        search_results = await self._web_search(query)
        
        # Pass directly to GPT with minimal instructions
        response = await self.llm.ainvoke(
            f"""User query: {query}
            
            Raw search results:
            {search_results}
            
            Provide helpful college recommendations based on these results.
            Respond in whatever format makes the most sense for the query."""
        )
        
        return {
            "query": query,
            "response": response.content,
            "results_analyzed": len(search_results)
        }

    async def _web_search(self, query: str) -> str:
        """Get raw search results as string"""
        try:
            results = self.search.results(query)
            return str(results)  # Pass complete raw results
        except Exception as e:
            return f"Search error: {str(e)}"

async def test_queries():
    recommender = WebSearchRecommender()
    
    queries = [
        "I have a 3.6 weighted GPA and 1280 SAT. What are good college matches?",
        "Looking for top-ranked mechanical engineering programs that accept 30+ ACT scores",
        "Suggest medium-sized universities in the Midwest for journalism majors",
        "Need colleges with full-tuition scholarships for international students with 4.0 GPA",
        "Which liberal arts colleges value debate team captains with 3.7 GPA?",
        "First-generation Hispanic student, 3.9 GPA but no SAT - best targets for pre-law?",
        "Colleges with strong autism support programs for computer science majors",
        "Suggest safety, target and reach schools for 3.5 GPA and 29 ACT biology majors",
        "Best test-optional universities for art history with 3.8 GPA",
        "Community college transfer with 3.4 GPA seeking business programs in Florida"
    ]
    
    for query in queries:
        print(f"\n{'='*60}\nQuery: {query}")
        results = await recommender.recommend(query)
        print(f"\nResponse:\n{results['response']}\n")
        print(f"Analyzed {results['results_analyzed']} search results")

if __name__ == "__main__":
    asyncio.run(test_queries())