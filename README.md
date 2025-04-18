# FinalProject


**Deployed Frontend** - https://finalprojectarvversion-chwvbdmqco4pwudyja49n6.streamlit.app/

**Deployed Backend** - https://final-project-deploy-343736309329.us-central1.run.app

## PowerPoint Presentation
https://northeastern-my.sharepoint.com/:p:/r/personal/singh_riya2_northeastern_edu/_layouts/15/Doc.aspx?sourcedoc=%7BC99D127B-A2F3-44E4-BCC0-055715F9247A%7D&file=FinalProjectProposal.pptx&wdOrigin=TEAMS-MAGLEV.p2p_ns.rwc&action=edit&mobileredirect=true

**Documents** - https://docs.google.com/document/d/1rpJwlVCqcSl3usIWlm807q2x4b6J6MDqk6OF6rDCimY/edit?usp=sharing

**Codelabs** - https://codelabs-preview.appspot.com/?file_id=1rpJwlVCqcSl3usIWlm807q2x4b6J6MDqk6OF6rDCimY/#0

**File Structure** 
.github/workflows - Github CI/CD Pipelines for github actions
Airflow/dags - Airflow code for converting to markdown and putting to S3.
POC- Initial prototyping
mcp - MCP Logic Implementation
multi-agents.egg-info - Config Files related to Agents
multi_Agents - Containes Different Agents
client.py - client for mcp
frontend.py - streamlit code
main.py - FastAPI Backend
server.py - For MCP Server
setup.py - setting up agents for the mcp server
style.css - To Beautify Frontend

## Architecture Diagram

![image](https://github.com/user-attachments/assets/5b6ad1f7-0718-4c11-b21b-b234bc05d446)

## 🎓 AI College Recommendation System – User Guide

Welcome to the AI College Recommendation System! This intelligent app helps you discover, compare, and explore top U.S. universities using structured and unstructured data combined with real-time search and global rankings.

## 🚀 What You Can Do
Get college recommendations based on your preferences (e.g., tuition, GPA, program type)

Compare colleges side-by-side on stats, courses, and faculty

Ask questions about specific programs (AI, CS, Data Science)

View QS global rankings

Get fallback answers using real-time web search

## 🖥️ How to Use the App
1. Open the App
You’ll be greeted by a clean Streamlit interface with a prompt box and submit button.

2. Enter a Prompt
Type in a natural language query. Here are some examples:

💡 “Recommend CS colleges with tuition under $40,000”

💡 “Compare Stanford and MIT for Artificial Intelligence programs”

💡 “What are the top 5 Data Science programs in the US?”

💡 “Where does Carnegie Mellon rank globally for AI?”

💡 “Do any California colleges offer faculty-led AI research?”

3. Submit and Wait
Click the "Submit" button. The app will:

Route your query to the appropriate AI agents

Process your request through structured (Snowflake), unstructured (Pinecone), or fallback (web search) pipelines

Use LLMs to summarize and format the answer

4. View the Results
You’ll see a personalized answer that may include:

Recommended colleges with key metrics

A side-by-side comparison table

Global ranking data (if requested)

Web-sourced content if no internal data matches

5. Export the Report
Optional: Download the results as a .txt file or Google Colab notebook (coming soon).


## Langgraph Flow

The LangGraph flow manages how prompts are routed through different agents (Snowflake, RAG, Web), using decision nodes and fallback mechanisms to ensure that the system always responds appropriately.

![image](https://github.com/user-attachments/assets/4b7e0caa-ada5-42eb-8290-770835e8659c)

![image](https://github.com/user-attachments/assets/b116d335-2a24-4fcd-b5dc-b696b8f8f76e)

## AI Disclosure







