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
    
    # Use Streamlit columns for the cards
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
            <div class="advisor-card disabled-card">
                <div class="card-icon">📊</div>
                <h3>Career Advisor</h3>
                <p>Discover career paths that match your skills and aspirations</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.button("Coming Soon", disabled=True)

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
                
                st.subheader("Recommended Colleges")
                for college in result["snowflake"]:
                    st.write(f"**{college.get('COLLEGE_NAME', 'Unknown')}**")
                    st.write(f"- Ranking: {college.get('RANKING', 'N/A')}")
                    st.write(f"- GPA Range: {college.get('MINIMUM_GPA', 'N/A')}")
                    st.write(f"- SAT Range: {college.get('SAT_RANGE', 'N/A')}")
                    st.write(f"- Tuition: ${college.get('TUITION_FEES', 'N/A')}")
                    st.write(f"- Location: {college.get('LOCATION', 'N/A')}")
                    if "PROGRAMS_OFFERED" in college:
                        st.write("- Strong Programs: " + ", ".join(college["PROGRAMS_OFFERED"]))
                    st.divider()
                
                if result["rag"]:
                    st.subheader("Supporting Information")
                    for doc in result["rag"]:
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
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Found {len(result['snowflake'])} matching colleges",
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


if __name__ == "__main__":
    main()