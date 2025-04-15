from typing import List, Dict
import asyncio
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain_openai import ChatOpenAI
import os
import json
from dotenv import load_dotenv

load_dotenv()

class WebSearchComparisonAgent:
    def __init__(self):
        self.search = GoogleSerperAPIWrapper(
            serper_api_key=os.getenv("SERPER_API_KEY"),
            k=10
        )
        self.llm = ChatOpenAI(
            model="gpt-4-turbo",
            temperature=0.3
        )

    async def recommend(self, comparison_query: str) -> Dict:
        """
        LangGraph-compatible method that returns:
        {
            "response": str,  # The comparison text
            "colleges": List[str],
            "aspects": List[str],
            "sources": List[Dict],
            "metadata": {
                "source": "web_search",
                "sources_analyzed": int
            }
        }
        """
        try:
            # Get the raw comparison from web search
            result = await self._generate_comparison(comparison_query)
            
            return {
                "response": result["comparison"],
                "colleges": result["colleges"],
                "aspects": [],  # Let LangGraph handle aspects
                "sources": result["sources"],
                "metadata": {
                    "source": "web_search",
                    "sources_analyzed": result["sources_analyzed"]
                }
            }
        except Exception as e:
            return {
                "response": f"Could not generate comparison: {str(e)}",
                "colleges": [],
                "aspects": [],
                "sources": [],
                "metadata": {
                    "source": "web_search_error",
                    "sources_analyzed": 0
                }
            }

    async def _generate_comparison(self, query: str) -> Dict:
        """Core comparison logic"""
        # Simple college extraction from query
        colleges = self._extract_colleges_simple(query)
        
        # Search for comparisons
        search_results = await self._web_search(query)
        
        # Generate natural language comparison
        comparison = await self._create_comparison_text(colleges, query, search_results)
        
        return {
            "comparison": comparison,
            "colleges": colleges,
            "sources": self._format_sources(search_results),
            "sources_analyzed": len(search_results.get('organic', []))
        }

    def _extract_colleges_simple(self, query: str) -> List[str]:
        """Basic college name extraction"""
        colleges = []
        common_colleges = ["MIT", "Stanford", "Harvard", "Yale", 
                         "Columbia", "NYU", "Caltech", "Georgia Tech"]
        for college in common_colleges:
            if college.lower() in query.lower():
                colleges.append(college)
                if len(colleges) == 2:
                    break
        return colleges

    async def _web_search(self, query: str) -> Dict:
        """Search with error handling"""
        try:
            results = self.search.results(query)
            return results if results else {"organic": []}
        except Exception:
            return {"organic": []}

    async def _create_comparison_text(self, colleges: List[str], 
                                   query: str,
                                   search_results: Dict) -> str:
        """Generates natural language comparison"""
        formatted_results = self._format_search_results(search_results)
        
        response = await self.llm.ainvoke(f"""
            Create a detailed comparison based on these search results.
            Original query: "{query}"
            Colleges: {colleges}
            
            Search Results:
            {formatted_results}

            Guidelines:
            1. Only include facts supported by the results
            2. Focus on aspects where both colleges have data
            3. Include specific numbers when available
            4. Structure the comparison naturally

            If no good comparison can be made, say:
            "Could not find enough comparable data for these colleges."
        """)
        return response.content

    def _format_search_results(self, results: Dict) -> str:
        """Formats results for LLM processing"""
        return "\n".join(
            f"{i+1}. {item.get('title', 'No title')}\n   {item.get('link', 'No link')}\n   {item.get('snippet', '')}"
            for i, item in enumerate(results.get('organic', [])[:8])
        )

    def _format_sources(self, results: Dict) -> List[Dict]:
        """Formats sources for output"""
        return [
            {"title": item.get("title", "No title"), "link": item.get("link", "")}
            for item in results.get('organic', [])[:3]
        ]

# Test function compatible with LangGraph
async def test_agent():
    agent = WebSearchComparisonAgent()
    test_queries = [
        "Compare MIT and Stanford for computer science",
        "Harvard vs Yale admissions statistics",
        "Georgia Tech versus Caltech engineering programs"
    ]
    
    for query in test_queries:
        print("\n" + "="*80)
        print(f"QUERY: {query}")
        
        result = await agent.recommend(query)
        print("\nRESPONSE:")
        print(result["response"])
        print(f"\nColleges: {result['colleges']}")
        print(f"Sources analyzed: {result['metadata']['sources_analyzed']}")

if __name__ == "__main__":
    asyncio.run(test_agent())