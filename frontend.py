# app.py (with New Chat button)
import streamlit as st
import requests
from pathlib import Path
# Config
BACKEND_URL = "http://localhost:8000"

def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Initialize session state
if 'current_page' not in st.session_state:
    st.session_state.current_page = "home"
if 'session_id' not in st.session_state:
    st.session_state.session_id = None
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'conversations' not in st.session_state:  # Store all conversations
    st.session_state.conversations = []
if 'current_conversation' not in st.session_state:
    st.session_state.current_conversation = None
# Replace the home_page() function with this updated version
# Update the home_page() function to enable the comparator
def home_page():
    local_css("style.css")
    
    st.markdown("""
    <style>
        .home-title {
            color: #1e293b !important;
        }
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <div class="home-container">
        <h1 class="home-title">College Advisor Pro</h1>
        <p class="home-subtitle">Your personalized guide to finding the perfect college</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.container():
            st.markdown("""
            <div class="advisor-card">
                <div class="card-icon">🎓</div>
                <h3>College Recommender</h3>
                <p>Find your ideal college based on GPA, test scores, and academic interests</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Get Started →", key="recommender_btn"):
                st.session_state.current_page = "college_recommender"
                st.rerun()
    
    with col2:
        with st.container():
            st.markdown("""
            <div class="advisor-card">
                <div class="card-icon">📊</div>
                <h3>College Comparator</h3>
                <p>Get a detailed comparison of colleges</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Compare Now →", key="comparator_btn"):
                st.session_state.current_page = "college_comparator"
                st.rerun()

def start_new_chat():
    """Start a fresh conversation"""
    if st.session_state.messages:
        # Save current conversation before clearing
        st.session_state.conversations.append({
            'id': len(st.session_state.conversations) + 1,
            'messages': st.session_state.messages.copy()
        })
    
    # Reset for new conversation
    st.session_state.messages = []
    response = requests.post(f"{BACKEND_URL}/create_session")
    st.session_state.session_id = response.json()["session_id"]
    st.rerun()

def display_conversation_history():
    with st.sidebar:
        st.button("➕ New Chat", on_click=start_new_chat)
        st.subheader("Conversation History")
        
        if not st.session_state.conversations:
            st.write("No previous conversations")
            return
            
        for conv in st.session_state.conversations:
            # Get first user message as title
            first_user_msg = next(
                (msg['content'] for msg in conv['messages'] if msg['role'] == 'user'), 
                "Empty conversation"
            )
            
            if st.button(f"{conv['id']}. {first_user_msg[:30]}...", key=f"conv_{conv['id']}"):
                # Load this conversation
                st.session_state.messages = conv['messages'].copy()
                st.rerun()

def college_recommender_page():
    st.markdown("""
    <style>
        .stChatMessage, .stMarkdown, .stMarkdown p {
            color: black !important;
        }
    </style>
    """, unsafe_allow_html=True)
    display_conversation_history()
    
    # Back button at top right
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("College Recommendations")
    with col2:
        if st.button("← Back to Home"):
            st.session_state.current_page = "home"
            st.session_state.session_id = None
            st.session_state.messages = []
            st.rerun()
    
    # Session management
    if not st.session_state.session_id:
        response = requests.post(f"{BACKEND_URL}/create_session")
        st.session_state.session_id = response.json()["session_id"]
    
    # Display current conversation
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg.get("result"):
                result = msg["result"]
                
                # Handle safety/off-topic messages
                if result.get("message"):
                    st.warning(result["message"])
                    continue
                
                # Handle fallback notification
                if result.get("fallback_used"):
                    st.info(result["fallback_message"])
                
                # Display results if available
                if result.get("data"):
                    data = result["data"]
                    
                    # Display college results
                    if data.get("colleges"):
                        st.subheader("Recommended Colleges")
                        for college in data["colleges"]:
                            st.write(f"**{college.get('COLLEGE_NAME', 'Unknown')}**")
                            st.write(f"- GPA Range: {college.get('MINIMUM_GPA', 'N/A')}")
                            st.write(f"- SAT Range: {college.get('SAT_RANGE', 'N/A')}")
                            st.divider()
                    else:
                        st.write("No matching colleges found in our database")
                    
                    # Display web results if fallback was used
                    if data.get("web_results"):
                        st.subheader("Web Recommendations")
                        for web_result in data["web_results"]:
                            st.write(web_result.get("text", ""))
                            st.divider()
                    
                    # Display RAG documents
                    if data.get("documents"):
                        st.subheader("Supporting Information")
                        for doc in data["documents"]:
                            st.write(doc.get("text", ""))
                            if "metadata" in doc:
                                st.caption(f"Source: {doc['metadata'].get('source', 'Unknown')}")
                            st.divider()
    
    # New prompt input
    if prompt := st.chat_input("Example: 'Find colleges for CS with 3.8 GPA'"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.write(prompt)
        
        with st.spinner("Finding best colleges..."):
            try:
                response = requests.post(
                    f"{BACKEND_URL}/recommend",
                    json={
                        "prompt": prompt,
                        "session_id": st.session_state.session_id
                    }
                )
                result = response.json()
                
                # Format the assistant response
                if result.get("message"):  # Safety/off-topic response
                    assistant_response = result["message"]
                elif result.get("data"):  # Normal results
                    college_count = len(result["data"].get("colleges", []))
                    web_count = len(result["data"].get("web_results", []))
                    
                    if college_count > 0:
                        assistant_response = f"Found {college_count} matching colleges"
                    elif web_count > 0:
                        assistant_response = "Found web-based recommendations"
                    else:
                        assistant_response = "No matching colleges found"
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": assistant_response,
                    "result": result
                })
                
                st.rerun()
            except Exception as e:
                st.error(f"Error: {str(e)}")

# Add this new function for the comparator page
def college_comparator_page():
    st.markdown("""
    <style>
        .stChatMessage, .stMarkdown, .stMarkdown p {
            color: black !important;
        }
    </style>
    """, unsafe_allow_html=True)
    display_conversation_history()
    
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("College Comparisons")
    with col2:
        if st.button("← Back to Home"):
            st.session_state.current_page = "home"
            st.session_state.session_id = None
            st.session_state.messages = []
            st.rerun()
    
    # Session management
    if not st.session_state.session_id:
        response = requests.post(f"{BACKEND_URL}/create_session")
        st.session_state.session_id = response.json()["session_id"]
    
    # Display current conversation
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg.get("result"):
                result = msg["result"]
                
                if result.get("message"):  # Early response
                    st.warning(result["message"])
                    continue
                
                # Display comparison results
                st.write(result["response"])
                
                if result.get("fallback_used"):
                    st.info(f"Note: {result['fallback_message']}")
                
                # Show comparison details in expanders
                with st.expander("Comparison Details"):
                    if result["colleges"]:
                        st.write("**Colleges Compared:**")
                        st.write(", ".join(result["colleges"]))
                    
                    if result["aspects"]:
                        st.write("**Aspects Compared:**")
                        st.write(", ".join(result["aspects"]))
    
    # New prompt input
    if prompt := st.chat_input("Example: 'Compare MIT and Stanford for computer science'"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.write(prompt)
        
        with st.spinner("Analyzing comparison..."):
            try:
                response = requests.post(
                    f"{BACKEND_URL}/compare",
                    json={
                        "prompt": prompt,
                        "session_id": st.session_state.session_id
                    }
                )
                result = response.json()
                
                # Format the assistant response
                assistant_response = result["response"]
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": assistant_response,
                    "result": result
                })
                
                st.rerun()
            except Exception as e:
                st.error(f"Error: {str(e)}")

def main():
    local_css("style.css")
    
    # Handle navigation from button click
    if st.session_state.get('navigate_to_recommender'):
        st.session_state.current_page = "college_recommender"
        del st.session_state['navigate_to_recommender']
        st.rerun()
        
    if st.session_state.current_page == "home":
        home_page()
    elif st.session_state.current_page == "college_recommender":
        college_recommender_page()
    elif st.session_state.current_page == "college_comparator":  # Add this condition
        college_comparator_page()


if __name__ == "__main__":
    main()