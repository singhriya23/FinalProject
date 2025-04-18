# FinalProject


**Deployed Frontend** - https://finalprojectarvversion-jbsfhkzr7zmxr9kgot8uwe.streamlit.app/

**Deployed Backend** - https://final-project-deploy-343736309329.us-central1.run.app

## PowerPoint Presentation
https://northeastern-my.sharepoint.com/:p:/r/personal/singh_riya2_northeastern_edu/_layouts/15/Doc.aspx?sourcedoc=%7BC99D127B-A2F3-44E4-BCC0-055715F9247A%7D&file=FinalProjectProposal.pptx&wdOrigin=TEAMS-MAGLEV.p2p_ns.rwc&action=edit&mobileredirect=true

**Documents** - https://docs.google.com/document/d/1rpJwlVCqcSl3usIWlm807q2x4b6J6MDqk6OF6rDCimY/edit?tab=t.0#heading=h.bq6c011rmvk8

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

## Langgraph Flow

The LangGraph flow manages how prompts are routed through different agents (Snowflake, RAG, Web), using decision nodes and fallback mechanisms to ensure that the system always responds appropriately.

![image](https://github.com/user-attachments/assets/4b7e0caa-ada5-42eb-8290-770835e8659c)

![image](https://github.com/user-attachments/assets/b116d335-2a24-4fcd-b5dc-b696b8f8f76e)

## AI Disclosure







