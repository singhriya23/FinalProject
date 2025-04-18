
import streamlit as st
import requests
import json
from io import StringIO
from datetime import datetime
# Config
#BACKEND_URL = "http://localhost:8000"
BACKEND_URL = "https://final-project-deploy-343736309329.us-central1.run.app"
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

def home_page():
    local_css("style.css")
    
    # Full-width expanded header
    st.markdown("""
    <style>
        .header-container {
            text-align: center;
            margin-bottom: 30px;
        }
        .home-title {
            color: #1e293b;
            font-size: 2.5rem;
            margin-bottom: 10px;
        }
        .home-subtitle {
            color: #4b5563;
            font-size: 1.2rem;
            margin-bottom: 30px;
        }
        .feature-card {
            padding: 25px;
            border-radius: 12px;
            background-color: black;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 25px;
        }
        .feature-title {
            color: #4b5563;
            font-size: 1.5rem;
            margin-bottom: 15px;
        }
        .feature-description {
            color: #4b5563;
            margin-bottom: 20px;
        }
    </style>
    <div class="header-container">
        <h1 class="home-title">College Advisor Pro</h1>
        <p class="home-subtitle">Your personalized guide to finding the perfect college</p>
    </div>
    """, unsafe_allow_html=True)

    # Main content columns
    col1, col2 = st.columns(2, gap="large")

    with col1:
        # College Recommender Card
        with st.container():
            st.markdown("""
            <div class="feature-card">
                <h2 class="feature-title">College Recommender</h2>
                <p class="feature-description">
                    Find your ideal college based on GPA, test scores, and academic interests
                </p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Get Started →", key="recommender_btn", use_container_width=True):
                st.session_state.current_page = "college_recommender"
                st.rerun()

        # College Comparator Card
        with st.container():
            st.markdown("""
            <div class="feature-card">
                <h2 class="feature-title">College Comparator</h2>
                <p class="feature-description">
                    Get a detailed comparison between colleges
                </p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Compare Now →", key="comparator_btn", use_container_width=True):
                st.session_state.current_page = "college_comparator"
                st.rerun()

    with col2:
        # University Rankings Card
        with st.container():
            st.markdown("""
            <div class="feature-card">
                <h2 class="feature-title">University Rankings</h2>
                <p class="feature-description">
                    Explore QS World University Rankings and other ranking systems
                </p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("View Rankings →", key="rankings_btn", use_container_width=True):
                st.session_state.current_page = "university_rankings"
                st.rerun()

def start_new_chat():
    """Completely resets the current chat session without saving"""
    st.session_state.messages = []
    try:
        response = requests.post(f"{BACKEND_URL}/create_session")
        st.session_state.session_id = response.json().get("session_id")
        # Add welcome message
        st.session_state.messages = [{
            "role": "assistant",
            "content": "Hello! I can help you find colleges. Ask me anything about universities, programs, or admissions.",
            "result": {"message": "Welcome to College Advisor Pro"}
        }]
    except Exception as e:
        st.error(f"Failed to create new session: {str(e)}")
    st.rerun()

def display_conversation_history():
    """Displays saved conversations in sidebar with management options"""
    with st.sidebar:
        st.markdown("## Conversation History")
        
        if st.button("🆕 New Chat", use_container_width=True, 
                    help="Start a fresh conversation (current chat won't be saved)"):
            start_new_chat()
        
        st.markdown("---")
        st.markdown("<h3 style='color: white;'>Saved Conversations</h3>", unsafe_allow_html=True)
        
        if not st.session_state.get('conversations', []):
            st.info("No saved conversations yet")
        else:
            for conv in st.session_state.conversations:
                first_msg = next(
                    (m['content'] for m in conv['messages'] if m['role'] == 'user'),
                    "College recommendation"
                )
                
                with st.expander(f"🗓️ {conv['timestamp']}"):
                    st.caption(first_msg[:50] + ("..." if len(first_msg) > 50 else ""))
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        if st.button("Load", key=f"load_{conv['id']}"):
                            st.session_state.messages = [m.copy() for m in conv['messages']]
                            st.rerun()
                    with col2:
                        if st.button("❌", key=f"delete_{conv['id']}"):
                            st.session_state.conversations = [
                                c for c in st.session_state.conversations 
                                if c['id'] != conv['id']
                            ]
                            st.rerun()

def get_college_deadline(college_name: str):
    """Fetch application deadline for a specific college"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/deadline",
            json={"question": f"When is {college_name}'s application due?"},
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()  # Raise exception for bad status codes
        data = response.json()
        if data.get("success"):
            return data["response"]
        return data.get("message", "Deadline not available")
    except Exception as e:
        print(f"Error fetching deadline: {e}")
        return "Could not retrieve deadline"


def generate_report(messages):
    """Generates a clean text report from messages"""
    report_lines = []
    for msg in messages:
        role = "You" if msg["role"] == "user" else "Advisor"
        report_lines.append(f"\n{role}: {msg['content']}")
        
        if msg.get("result"):
            result = msg["result"]
            if result.get("message"):
                report_lines.append(f"Response: {result['message']}")
            elif result.get("response"):
                report_lines.append(f"Response: {result['response']}")
            elif result.get("data", {}).get("combined_output"):
                report_lines.append(f"\nRecommendation Summary:\n{result['data']['combined_output']}")
            
            if result.get("data", {}).get("snowflake"):
                report_lines.append("\nRecommended Colleges:")
                for college in result["data"]["snowflake"]:
                    report_lines.append(f"- {college.get('COLLEGE_NAME', 'Unknown')}")
    
    return "\n".join(report_lines)

def get_downloadable_content(result):
    """Convert the result into a downloadable text format"""
    buffer = StringIO()
    
    if isinstance(result, (dict, list)):
        json.dump(result, buffer, indent=2)
    else:
        buffer.write(str(result))
    
    buffer.seek(0)
    return buffer.getvalue()

def display_pure_response(result):
    """Improved version to properly display web search results"""
    if not result:
        return ""
    
    if isinstance(result, dict):
        # Handle fallback notice
        fallback_notice = ""
        if result.get("fallback_used"):
            fallback_notice = f"⚠️ {result.get('fallback_message', 'Showing web search results')}\n\n"
        
        # Check for web results first
        if result.get("data", {}).get("web_results"):
            web_results = result["data"]["web_results"]
            if isinstance(web_results, list) and web_results:
                response = fallback_notice
                for item in web_results:
                    if isinstance(item, dict) and item.get("text"):
                        response += item["text"] + "\n\n"
                return response.strip()
        
        # Fall back to message if available
        if result.get("message"):
            return fallback_notice + result["message"]
        
        return fallback_notice + "No response content available"
    
    return str(result)

def college_recommender_page():
    st.markdown("""
    <style>
        /* Main text styling */
        .stChatMessage, .stMarkdown, .stMarkdown p, .stText {
            color: #000000 !important;
        }
        
        /* Chat message bubbles */
        [data-testid="stChatMessage"] {
            background-color: #f8f9fa !important;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 12px;
            border: 1px solid #e1e4e8 !important;
        }
        
        /* Button styling */
        .stButton>button {
            border: 1px solid #4f46e5 !important;
            color: #4f46e5 !important;
            background-color: white !important;
            padding: 8px 16px !important;
            border-radius: 6px !important;
            margin: 4px !important;
        }
        
        .stButton>button:hover {
            background-color: #f5f3ff !important;
        }
        
        /* Input box */
        .stChatInputContainer {
            border-top: 1px solid #ddd !important;
            padding-top: 12px !important;
        }
        
        /* Success message */
        .stSuccess {
            font-size: 14px !important;
        }
        
        /* Sidebar styling */
        .sidebar .sidebar-content {
            padding: 2rem 1rem;
        }
    </style>
    """, unsafe_allow_html=True)

    # Header with back button (main content area)
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown("<h1 style='color: black;'>College Recommendations</h1>", unsafe_allow_html=True)
    with col2:
        if st.button("← Back to Home"):
            st.session_state.current_page = "home"
            st.session_state.session_id = None
            st.session_state.messages = []
            st.rerun()

    # Sidebar with conversation history
    with st.sidebar:
        st.markdown("<h3 style='color: white;'>Conversation History</h3>", unsafe_allow_html=True)
        
        # New Chat button - clears current conversation without saving
        if st.button("🆕 New Chat", use_container_width=True):
            st.session_state.messages = []
            try:
                response = requests.post(f"{BACKEND_URL}/create_session")
                st.session_state.session_id = response.json().get("session_id")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to create new session: {str(e)}")
        
        st.markdown("---")
        st.markdown("<h3 style='color: white;'>Saved Recommendations</h3>", unsafe_allow_html=True)
        
        if not st.session_state.get('conversations', []):
            st.info("No saved recommendations yet")
        else:
            for conv in st.session_state.conversations:
                # Use custom name if available, otherwise use timestamp
                display_name = conv.get('name', conv['timestamp'])
                
                # Get first user message or default text
                first_msg = next(
                    (m['content'] for m in conv['messages'] if m['role'] == 'user'),
                    "Saved recommendation"
                )
                
                # Display each saved conversation with options
                with st.expander(f"📁 {display_name}"):
                    st.markdown(f"<p style='color: white; font-size: 0.8rem;'>{first_msg[:50] + ('...' if len(first_msg) > 50 else '')}</p>", unsafe_allow_html=True)
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        if st.button("Load", key=f"load_{conv['id']}"):
                            st.session_state.messages = conv['messages'].copy()
                            st.rerun()
                    with col2:
                        if st.button("❌", key=f"delete_{conv['id']}"):
                            st.session_state.conversations = [
                                c for c in st.session_state.conversations 
                                if c['id'] != conv['id']
                            ]
                            st.rerun()
        
        st.markdown("---")   
        st.markdown("<h3 style='color: white;'>College Deadline Lookup</h3>", unsafe_allow_html=True)

        # Deadline lookup widget
        college_for_deadline = st.text_input(
            "Check application deadline:",
            placeholder="Enter college name (e.g. MIT)",
            key="deadline_lookup",
            label_visibility="collapsed"
        )

        if college_for_deadline:
            with st.spinner(f"Checking {college_for_deadline}'s deadline..."):
                try:
                    response = requests.post(
                        f"{BACKEND_URL}/deadline",
                        json={"question": f"When is {college_for_deadline}'s application due?"},
                        headers={"Content-Type": "application/json"}
                    )
                    response.raise_for_status()
                    data = response.json()
                    if data.get("success"):
                        st.info(data["response"])
                    else:
                        st.error(data.get("message", "Deadline not available"))
                except requests.exceptions.HTTPError as http_err:
                    st.error(f"HTTP error occurred: {http_err}")
                except Exception as e:
                    st.error(f"Failed to fetch deadline: {str(e)}")
                    
        

    # Initialize session if needed
    if not st.session_state.session_id:
        try:
            response = requests.post(f"{BACKEND_URL}/create_session")
            st.session_state.session_id = response.json().get("session_id")
            # Add welcome message only if no messages exist
            if not st.session_state.messages:
                st.session_state.messages = [{
                    "role": "assistant",
                    "content": "Hello! I can help you find colleges. Ask me anything about universities, programs, or admissions.",
                    "result": {"message": "Welcome to College Advisor Pro"}
                }]
        except Exception as e:
            st.error(f"Failed to create session: {str(e)}")
            return

    # Display all messages in the current conversation
    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            if msg["role"] == "user":
                st.write(msg["content"])
            elif msg["role"] == "assistant":
                if msg.get("result"):
                    response_content = display_pure_response(msg["result"])
                    st.markdown(response_content)
                else:
                    st.write(msg["content"])
                
                # Action buttons for assistant responses
                if msg["role"] == "assistant":
                    cols = st.columns([1, 1, 2])
                    
                    with cols[0]:  # Download button
                        if st.button(f"📥 Download", key=f"download_{i}"):
                            download_content = generate_report([msg])
                            st.download_button(
                                label="Confirm Download",
                                data=download_content,
                                file_name=f"college_recommendation_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                                mime="text/plain",
                                key=f"real_download_{i}"
                            )
                    
                    with cols[1]:  # Save button
                        if st.button(f"💾 Save", key=f"save_{i}"):
                            st.session_state.save_dialog_open = True
                            st.session_state.save_dialog_for = i

                    # Streamlit-native modal dialog
                    if st.session_state.get('save_dialog_open') and st.session_state.get('save_dialog_for') == i:
                        with st.form(key=f"save_form_{i}"):
                            save_name = st.text_input(
                                "Enter a name for this conversation:",
                                value=f"College Recommendations {datetime.now().strftime('%Y-%m-%d')}",
                                key=f"save_name_input_{i}"
                            )
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("Save"):
                                    if not save_name.strip():
                                        st.warning("Please enter a name")
                                    else:
                                        new_conv = {
                                            'id': len(st.session_state.conversations) + 1,
                                            'name': save_name.strip(),
                                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M"),
                                            'messages': [m.copy() for m in st.session_state.messages]
                                        }
                                        
                                        if 'conversations' not in st.session_state:
                                            st.session_state.conversations = []
                                        
                                        st.session_state.conversations.append(new_conv)
                                        st.session_state.save_dialog_open = False
                                        st.toast(f"Saved as '{save_name}'")
                                        st.rerun()
                            with col2:
                                if st.form_submit_button("Cancel"):
                                    st.session_state.save_dialog_open = False
                                    st.rerun()

    # Handle new user input
    if prompt := st.chat_input("Ask about colleges..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.spinner("Researching colleges..."):
            try:
                # Get backend response
                response = requests.post(
                    f"{BACKEND_URL}/recommend",
                    json={
                        "prompt": prompt,
                        "session_id": st.session_state.session_id
                    },
                    timeout=120
                )
                result = response.json()
                
                # Add assistant response
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": display_pure_response(result),
                    "result": result
                })
                
                st.rerun()
                
            except requests.Timeout:
                st.error("Request timed out. Please try again.")
            except Exception as e:
                st.error(f"Error getting recommendations: {str(e)}")

def college_comparator_page():
    st.markdown("""
    <style>
        .stChatMessage, .stMarkdown, .stMarkdown p {
            color: black !important;
        }
        /* Add the same styling as recommender page for consistency */
        [data-testid="stChatMessage"] {
            background-color: #f8f9fa !important;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 12px;
            border: 1px solid #e1e4e8 !important;
        }
        .stButton>button {
            border: 1px solid #4f46e5 !important;
            color: #4f46e5 !important;
            background-color: white !important;
            padding: 8px 16px !important;
            border-radius: 6px !important;
            margin: 4px !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Header with back button
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("College Comparisons")
    with col2:
        if st.button("← Back to Home"):
            st.session_state.current_page = "home"
            st.session_state.session_id = None
            st.session_state.messages = []
            st.rerun()

    # Add conversation history sidebar (same as recommender)
    with st.sidebar:
        st.markdown("## Conversation History")
        
        # New Chat button
        if st.button("🆕 New Chat", use_container_width=True):
            st.session_state.messages = []
            try:
                response = requests.post(f"{BACKEND_URL}/create_session")
                st.session_state.session_id = response.json().get("session_id")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to create new session: {str(e)}")
        
        st.markdown("---")
        st.markdown("### Saved Conversations")
        
        if not st.session_state.get('conversations', []):
            st.info("No saved conversations yet")
        else:
            for conv in st.session_state.conversations:
                first_msg = next(
                    (m['content'] for m in conv['messages'] if m['role'] == 'user'),
                    "College comparison"
                )
                
                with st.expander(f"🗓️ {conv['timestamp']}"):
                    st.caption(first_msg[:50] + ("..." if len(first_msg) > 50 else ""))
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        if st.button("Load", key=f"load_{conv['id']}"):
                            st.session_state.messages = [m.copy() for m in conv['messages']]
                            st.rerun()
                    with col2:
                        if st.button("❌", key=f"delete_{conv['id']}"):
                            st.session_state.conversations = [
                                c for c in st.session_state.conversations 
                                if c['id'] != conv['id']
                            ]
                            st.rerun()

    # Initialize session if needed
    if not st.session_state.session_id:
        try:
            response = requests.post(f"{BACKEND_URL}/create_session")
            st.session_state.session_id = response.json().get("session_id")
            if not st.session_state.messages:
                st.session_state.messages = [{
                    "role": "assistant",
                    "content": "Hello! I can help you compare colleges. Ask me things like 'Compare MIT and Stanford for computer science'",
                    "result": {"message": "Welcome to College Comparator"}
                }]
        except Exception as e:
            st.error(f"Failed to create session: {str(e)}")
            return

    # Display all messages in the current conversation
    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            if msg["role"] == "user":
                st.write(msg["content"])
            
            elif msg.get("result"):
                result = msg["result"]
                
                if result.get("message"):
                    st.write(result["message"])
                elif result.get("response"):
                    st.write(result["response"])
                
                if result.get("fallback_used"):
                    st.info(f"Note: {result['fallback_message']}")
                
                # Add comparison details expander
                if result.get("colleges") or result.get("aspects"):
                    with st.expander("Comparison Details"):
                        if result.get("colleges"):
                            st.write("**Colleges Compared:**")
                            st.write(", ".join(result["colleges"]))
                        
                        if result.get("aspects"):
                            st.write("**Aspects Compared:**")
                            st.write(", ".join(result["aspects"]))
                
                # Add action buttons for assistant responses
                if msg["role"] == "assistant":
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button(f"📥 Download", key=f"download_{i}"):
                            download_content = generate_report([msg])
                            st.download_button(
                                label="Confirm Download",
                                data=download_content,
                                file_name=f"college_comparison_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                                mime="text/plain",
                                key=f"real_download_{i}"
                            )
                    with col2:
                        if st.button(f"💾 Save", key=f"save_{i}"):
                            # Create new conversation entry
                            new_conv = {
                                'id': len(st.session_state.conversations) + 1,
                                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M"),
                                'messages': [{
                                    "role": m["role"],
                                    "content": m["content"],
                                    "result": m.get("result", {}).copy() if isinstance(m.get("result"), dict) else m.get("result")
                                } for m in st.session_state.messages]
                            }
                            
                            if 'conversations' not in st.session_state:
                                st.session_state.conversations = []
                            
                            st.session_state.conversations.append(new_conv)
                            st.toast("Conversation saved!", icon="✅")
                            st.rerun()

    # Handle new user input
    if prompt := st.chat_input("Example: 'Compare MIT and Stanford for computer science'"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
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
                assistant_response = result.get("response", "No comparison results available")
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": assistant_response,
                    "result": result
                })
                
                st.rerun()
            except Exception as e:
                st.error(f"Error: {str(e)}")

def university_rankings_page():
    st.markdown("""
    <style>
        .stChatMessage, .stMarkdown, .stMarkdown p {
            color: black !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Header with back button
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("University Rankings")
        st.markdown("Ask about QS World University Rankings")
    with col2:
        if st.button("← Back to Home"):
            st.session_state.current_page = "home"
            st.rerun()
    
    # Initialize messages if not exists
    if 'ranking_messages' not in st.session_state:
        st.session_state.ranking_messages = [
            {
                "role": "assistant", 
                "content": "I can answer questions about QS World University Rankings. Ask me things like:\n\n- What's MIT's ranking?\n- Show top 10 universities\n- Which university is ranked 5th?"
            }
        ]
    
    # Display chat messages
    for msg in st.session_state.ranking_messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg.get("additional_context"):
                with st.expander("More context"):
                    st.write(msg["additional_context"])
    
    # Handle user input
    if prompt := st.chat_input("Ask about university rankings..."):
        # Add user message
        st.session_state.ranking_messages.append({"role": "user", "content": prompt})
        
        with st.spinner("Checking rankings..."):
            try:
                # Call the backend endpoint
                response = requests.post(
                    f"{BACKEND_URL}/university_rankings",
                    json={"question": prompt}
                )
                result = response.json()
                
                # Add assistant response
                assistant_msg = {
                    "role": "assistant",
                    "content": result["answer"]
                }
                
                if result.get("additional_context"):
                    assistant_msg["additional_context"] = result["additional_context"]
                
                st.session_state.ranking_messages.append(assistant_msg)
                st.rerun()
                
            except Exception as e:
                st.error(f"Error getting rankings: {str(e)}")
                st.session_state.ranking_messages.append({
                    "role": "assistant",
                    "content": "Sorry, I couldn't retrieve the rankings. Please try again."
                })
                st.rerun()


def main():
    local_css("style.css")
    
    # Handle ranking button click
    if st.session_state.get('show_ranking_chat') is None:
        st.session_state.show_ranking_chat = False
    
    if st.session_state.get('navigate_to') == 'show_ranking_chat':
        st.session_state.show_ranking_chat = not st.session_state.show_ranking_chat
        st.rerun()
        
    if st.session_state.current_page == "home":
        home_page()
    elif st.session_state.current_page == "college_recommender":
        college_recommender_page()
    elif st.session_state.current_page == "college_comparator":
        college_comparator_page()
    elif st.session_state.current_page == "university_rankings":  # Add this condition
        university_rankings_page()


if __name__ == "__main__":
    main()