from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import requests
import dotenv
from byaldi import RAGMultiModalModel

# Load environment
dotenv.load_dotenv("project.env")
ELEVEN_LABS_KEY = os.getenv("ELEVEN_LABS_KEY")
if not ELEVEN_LABS_KEY:
    raise ValueError("ELEVEN_LABS_KEY environment variable is not set or empty")

app = FastAPI()

# CORS middleware
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base URL for ElevenLabs API
BASE_URL = "https://api.elevenlabs.io/v1"

# Helper function to make API requests
def make_request(method, endpoint, json_data=None):
    """Make a request to the ElevenLabs API"""
    url = f"{BASE_URL}{endpoint}"
    headers = {
        "xi-api-key": ELEVEN_LABS_KEY,
        "Content-Type": "application/json"
    }
    
    response = requests.request(
        method=method,
        url=url,
        headers=headers,
        json=json_data
    )
    
    if response.status_code not in [200, 201]:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"ElevenLabs API error: {response.text}"
        )
    
    return response.json()

### Pydantic models for your endpoints

class CreateAgentRequest(BaseModel):
    company_name: str
    company_url: str

class SetKnowledgeBaseRequest(BaseModel):
    agent_id: str
    url: str
    doc_name: str

class UpdateAgentVarsRequest(BaseModel):
    agent_id: str
    company_name: str
    company_url: str


class PerplexityQueryRequest(BaseModel):
    query: str

class QueryDocumentRequest(BaseModel):
    query: str

class GetAgentInfoRequest(BaseModel):
    agent_id: str

### Endpoints

@app.post("/create_agent")
async def create_agent(req: CreateAgentRequest):
    """
    Creates a new agent configured for the given company name and URL,
    sets the first message, system prompt with dynamic placeholders, and returns the agent_id.
    """
    # Build the initial configuration
    body = {
        "name": f"Agent for {req.company_name}",
        "conversation_config": {
            "agent": {
                "first_message": f"Hello, I'm Maya from {req.company_name}. How can I help you today?",
                "prompt": {
                    "prompt": (
                        f"You are a helpful customer-service assistant for {req.company_name}. "
                        f"You may consult the knowledge base (see URL {req.company_url}) when needed. "
                        "If you cannot find the answer, respond that you don't know."
                    )
                }
            }
        }
    }

    resp = make_request("POST", "/convai/agents/create", body)
    return {"agent_id": resp.get("agent_id"), "name": resp.get("name")}

@app.post("/set_knowledge_base")
async def set_knowledge_base(req: SetKnowledgeBaseRequest):
    """
    Create a knowledge-base document from the given URL and attach it to the specified agent.
    """
    # Step 1: create document from URL
    doc_body = {
        "url": req.url,
        "name": req.doc_name
    }
    doc_resp = make_request("POST", "/convai/knowledge-base/create-from-url", doc_body)
    doc_id = doc_resp.get("id")

    # Step 2: update agent to include the knowledge_base
    update_body = {
        "conversation_config": {
            "agent": {
                "prompt": {
                    "knowledge_base": [
                        {
                            "type": "url",
                            "name": req.doc_name,
                            "id": doc_id,
                            "usage_mode": "auto"
                        }
                    ]
                }
            }
        }
    }
    agent_resp = make_request("PUT", f"/convai/agents/{req.agent_id}", update_body)
    return {"agent_id": req.agent_id, "doc_id": doc_id, "agent_update": agent_resp}
@app.post("/update_agent_vars")
async def update_agent_vars(req: UpdateAgentVarsRequest):
    """
    Update the dynamic variables (company name and URL placeholders) on an existing agent,
    and also update first message & prompt accordingly.
    This function preserves existing tools (tool_ids and built_in_tools) so they don't get removed.
    """
    # First, get the current agent configuration to preserve tools
    current_agent = make_request("GET", f"/convai/agents/{req.agent_id}", None)
    
    # Extract existing tools from the current configuration
    existing_tool_ids = []
    existing_built_in_tools = []
    
    if "conversation_config" in current_agent:
        agent_config = current_agent["conversation_config"].get("agent", {})
        prompt_config = agent_config.get("prompt", {})
        
        # Preserve tool_ids (server/client tools)
        if "tool_ids" in prompt_config:
            existing_tool_ids = prompt_config["tool_ids"]
        
        # Preserve built_in_tools (system tools like end_call, language_detection)
        if "built_in_tools" in prompt_config:
            existing_built_in_tools = prompt_config["built_in_tools"]
    
    # Build the update body with the new prompt and preserved tools
    update_body = {
        "conversation_config": {
            "agent": {
                "first_message": f"Hello! I'm Maya from {req.company_name}. I'm here to help answer your questions and provide information. How can I assist you today?",
                "prompt": {
                    "prompt": f"""You are Maya, a professional and knowledgeable customer service assistant representing {req.company_name}. The website is {req.company_url}. Your role is to provide excellent customer support by being helpful, accurate, and empathetic.

CORE IDENTITY & PERSONALITY:
- You are warm, friendly, and professional in all interactions
- You speak naturally and conversationally while maintaining professionalism
- You're patient and understanding, even with frustrated or confused customers
- You show genuine interest in helping solve the customer's problems
- You use the customer's name when provided to personalize the conversation

CAPABILITIES & KNOWLEDGE SOURCES:
1. Your Training Knowledge: Use your general knowledge base first for common questions
2. Company Knowledge Base: Reference the company information at {req.company_url} for company-specific details
3. Perplexity AI Tool: Use the query_perplexity tool for:
   - Real-time information (current events, news, weather, stock prices)
   - Recent data that may have changed since your training
   - Fact verification when you need current information
   - Any topic requiring up-to-date web search results

RESPONSE GUIDELINES:
- Always prioritize accuracy over speed - if you're unsure, say so
- Keep responses concise but complete (aim for 2-4 sentences unless more detail is needed)
- Use bullet points or numbered lists only when presenting multiple options or steps
- Avoid jargon unless the customer uses it first
- If you need to use the Perplexity tool, do so seamlessly without announcing it
- Never make up information - if you don't know something and can't find it, admit it honestly

WHEN TO USE THE PERPLEXITY TOOL:
✓ Customer asks about current events, news, or recent updates
✓ Questions about real-time data (weather, stock prices, sports scores, etc.)
✓ Information that changes frequently or may be outdated in your training
✓ Fact-checking requests or verification of current information
✓ Topics explicitly requiring a web search
✓ Company news or updates not in the knowledge base

✗ DO NOT use for: Basic company info already in knowledge base, general knowledge questions, creative tasks, or opinions

HANDLING DIFFICULT SITUATIONS:
- If the customer is frustrated, acknowledge their feelings: "I understand this is frustrating..."
- If you can't help, offer alternatives: "While I can't directly help with that, I can connect you with someone who can..."
- If information is unclear, ask clarifying questions: "Just to make sure I understand correctly..."
- If there's an error or mistake, own it: "I apologize for the confusion..."

ESCALATION SCENARIOS:
When you encounter these situations, politely offer to escalate:
- Technical issues you cannot resolve
- Billing disputes or refund requests
- Complaints requiring management attention
- Requests for services outside your scope
- Any situation where the customer explicitly asks for a human agent

Use this format: "I'd be happy to connect you with [specific team/person] who can better assist you with this. Would you like me to do that?"

CONVERSATION FLOW:
1. Greet warmly and understand the request
2. Gather necessary information through friendly questions
3. Provide clear, accurate information using appropriate sources
4. Confirm the customer's needs are met
5. Offer additional help before closing
6. Thank them for contacting {req.company_name}

IMPORTANT REMINDERS:
- Never share sensitive customer information
- Always respect privacy and confidentiality
- Stay on-brand and aligned with {req.company_name}'s values
- If you're unsure about company policy, say so and offer to check with a supervisor
- Maintain a positive, solution-oriented attitude throughout the conversation

Remember: Your goal is not just to answer questions, but to create a positive experience that leaves the customer feeling heard, helped, and valued."""
                }
            }
        }
    }
    
    # Add the preserved tools back to the prompt configuration
    if existing_tool_ids or existing_built_in_tools:
        if existing_tool_ids:
            update_body["conversation_config"]["agent"]["prompt"]["tool_ids"] = existing_tool_ids
        if existing_built_in_tools:
            update_body["conversation_config"]["agent"]["prompt"]["built_in_tools"] = existing_built_in_tools
    
    # Update the agent
    resp = make_request("PATCH", f"/convai/agents/{req.agent_id}", update_body)
    
    return {
        "agent_id": req.agent_id, 
        "update_resp": resp,
        "preserved_tool_ids": existing_tool_ids,
        "preserved_built_in_tools": existing_built_in_tools
    }


@app.post("/index_document")
async def index_document(req: IndexDocumentRequest):
    """
    Index a document into the knowledge base.
    """
    RAG = RAGMultiModalModel.from_pretrained("vidore/colpali-v1.3", device="mps", index_root="indexes")
    RAG.index(input_path="./documents", index_name="index_thing")
    return True

@app.post("/query_document")
async def query_document(req: QueryDocumentRequest):
    """
    Query a document from the knowledge base.
    """
    RAG = RAGMultiModalModel.from_index(index_path="index_thing", index_root="indexes", device="mps")
    resp = RAG.query(query=req.query)
    return resp

@app.post("/get_agent_info")
async def get_agent_info(req: GetAgentInfoRequest):
    """
    Fetch information about the agent.
    """
    resp = make_request("GET", f"/convai/agents/{req.agent_id}", None)
    return resp

@app.post("/list_agents")
async def list_agents():
    """
    List all agents in your workspace.
    """
    resp = make_request("GET", "/convai/agents", None)
    return resp

@app.post("/query-perplexity")
async def query_perplexity(req: PerplexityQueryRequest):
    """
    Query Perplexity AI with a question and return the response.
    Uses the latest Sonar model for fast, accurate answers with real-time web search.
    """
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.getenv('PERPLEXITY_KEY')}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "sonar",  # Updated to use the latest Sonar model (replaces deprecated llama models)
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful AI assistant that provides accurate, concise, and well-sourced answers. Always cite your sources when providing factual information."
            },
            {
                "role": "user",
                "content": req.query
            }
        ],
        "temperature": 0.2,  # Lower temperature for more factual, focused responses
        "max_tokens": 1024,
        "return_citations": True,  # Enable citations for source attribution
        "return_images": False  # Disable images for faster responses
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Perplexity API error: {response.text}"
        )
    
    result = response.json()
    
    # Extract the assistant's response and citations
    if "choices" in result and len(result["choices"]) > 0:
        answer = result["choices"][0]["message"]["content"]
        
        # Extract citations if available
        citations = []
        if "citations" in result:
            citations = result["citations"]
        
        return {
            "query": req.query,
            "answer": answer,
            "citations": citations,
            "model": result.get("model", "sonar"),
            "usage": result.get("usage", {})
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Unexpected response format from Perplexity API"
        )
