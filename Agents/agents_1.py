import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from newintent.dynamic_handler import DynamicIntentHandler
from newintent.safety_system import SafetySystem

class CollegeRecommender:
    def __init__(self):
        self.safety_system = SafetySystem()
        self.dynamic_handler = DynamicIntentHandler()
        self.conversation_history: List[Dict] = []
        
        # Initialize your actual college recommendation tools here
        # self.college_agent = initialize_your_college_agent()

    async def handle_query(self, query: str) -> Dict:
        """Main entry point for handling user queries"""
        if not query.strip():
            return self._build_response("Please enter a valid question.")
        
        # Run safety checks first
        safety_result = await self.safety_system.check_query(
            query, 
            self.conversation_history
        )
        
        if not safety_result["safe"]:
            response = safety_result["response"]
            self._update_history(query, response, "safety_block")
            return self._build_response(response)
        
        try:
            # Try normal college recommendation flow
            if self._is_college_related(query):
                response = await self._handle_college_query(query)
                self._update_history(query, response, "college_response")
                return self._build_response(response)
            
            # Handle other valid but non-college queries
            response = await self.dynamic_handler.handle_unknown(
                query, 
                self.conversation_history
            )
            self._update_history(query, response, "general_response")
            return self._build_response(response)
            
        except Exception as e:
            # Fallback for unexpected errors
            error_response = "Sorry, I encountered an error. Try asking about colleges instead."
            self._update_history(query, error_response, "error")
            return self._build_response(error_response)

    async def _handle_college_query(self, query: str) -> str:
        """Process college-specific queries"""
        # Replace this with your actual college recommendation logic
        # For now using a mock implementation
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
        """Basic college intent detection"""
        college_keywords = {
            "college", "university", "degree", "major", 
            "gpa", "tuition", "admission", "campus",
            "engineering", "computer science", "dorm"
        }
        return any(keyword in query.lower() for keyword in college_keywords)

    def _update_history(self, query: str, response: str, context: str):
        """Maintain conversation context"""
        self.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "response": response,
            "context": context,
            "turns": len(self.conversation_history) + 1
        })
        
        # Keep history manageable
        if len(self.conversation_history) > 20:
            self.conversation_history.pop(0)

    def _build_response(self, message: str, metadata: Optional[Dict] = None) -> Dict:
        """Standardize response format"""
        return {
            "response": message,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }

async def interactive_demo():
    """Command-line demo interface"""
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
    # For production use:
    # import uvicorn
    # uvicorn.run(app, host="0.0.0.0", port=8000)
    
    # For testing:
    asyncio.run(interactive_demo())