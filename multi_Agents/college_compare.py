from typing import Dict, Any
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import asyncio

class ComparisonDetector:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4-turbo", temperature=0)
        # Fixed prompt template with escaped curly braces
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at detecting college comparison requests. Analyze the user's query and determine:
            1. If it's a comparison request (is_comparison)
            2. Which colleges are being compared (colleges)
            3. What aspects are being compared (comparison_aspects)

            Rules:
            - Always return EXACTLY 2 colleges if is_comparison=true
            - Standardize names (use "MIT" not "Massachusetts Institute of Technology")
            - Extract 1-3 key comparison aspects

            Respond with VALID JSON ONLY:
            {{
                "is_comparison": boolean,
                "colleges": ["college1", "college2"],
                "comparison_aspects": ["aspect1", "aspect2"]
            }}"""),
            ("human", "{query}")
        ])
        self.chain = self.prompt_template | self.llm

    async def detect(self, query: str) -> Dict[str, Any]:
        """Detect comparison with robust error handling"""
        try:
            response = await self.chain.ainvoke({"query": query})
            # Handle cases where response might be markdown with json code blocks
            content = response.content
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            return json.loads(content)
            
        except Exception as e:
            print(f"⚠️ Detection error for '{query}': {str(e)}")
            return {
                "is_comparison": False,
                "colleges": [],
                "comparison_aspects": []
            }

async def run_tests():
    detector = ComparisonDetector()
    
    test_queries = [
        "What's the weather like today?"
    ]
    
    print("🏫 Comparison Detector Test Suite\n" + "="*50)
    
    for query in test_queries:
        result = await detector.detect(query)
        
        print(f"\n🔍 Query: '{query}'")
        print(f"• Is comparison: {result['is_comparison']}")
        if result['is_comparison']:
            print(f"• Colleges: {', '.join(result['colleges'])}")
            print(f"• Aspects: {', '.join(result['comparison_aspects'])}")
        else:
            print("• Not a comparison request")
            
        print("-"*50)

if __name__ == "__main__":
    asyncio.run(run_tests())