import asyncio
import logging
import os
import sys
from pathlib import Path
import shutil

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.adk.tools.retrieval.vertex_ai_rag_retrieval import VertexAiRagRetrieval
from mcp import StdioServerParameters
import vertexai
from vertexai import agent_engines
from vertexai.preview.reasoning_engines import AdkApp
from vertexai.preview import rag

load_dotenv(os.path.join(os.path.abspath(os.path.dirname(__file__)), ".env"), override=True)

# Debug mode configuration
DEBUG = os.environ.get("DEBUG", "False") == "True"

if DEBUG:
  os.environ['GRPC_VERBOSITY'] = 'DEBUG'
  os.environ['GRPC_TRACE'] = 'all'
  logging.basicConfig(level=logging.DEBUG)
  logging.getLogger('google').setLevel(logging.DEBUG)
  logging.getLogger('google.auth').setLevel(logging.DEBUG)
  logging.getLogger('google.api_core').setLevel(logging.DEBUG)

# Google Cloud Platform - Core Configuration
GCP_PROJECT_ID = os.environ["GCP_PROJECT_ID"]  # string; GCP project ID
GCP_LOCATION = os.environ["GCP_LOCATION"]  # string; GCP region (us-central1, us-east4, etc.)
GCP_STAGING_BUCKET = os.environ["GCP_STAGING_BUCKET"]  # string; gs://bucket-name
GCP_VERTEXAI_ENABLED = os.environ["GCP_VERTEXAI_ENABLED"]  # bool string; must be "True" for RAG

# Chronicle SIEM Configuration
CHRONICLE_CUSTOMER_ID = os.environ["CHRONICLE_CUSTOMER_ID"]  # uuid4; Chronicle customer UUID
CHRONICLE_REGION = os.environ.get("CHRONICLE_REGION", "us")  # string; Chronicle region (us, europe, asia)
CHRONICLE_SERVICE_ACCOUNT_PATH = os.environ["CHRONICLE_SERVICE_ACCOUNT_PATH"]  # abs path; SA JSON file

# SOAR Platform Configuration
SOAR_URL = os.environ["SOAR_URL"]  # string; https://[YOUR-ID].siemplify-soar.com:443
SOAR_API_KEY = os.environ["SOAR_API_KEY"]  # uuid4; SOAR authentication key

# Google Threat Intelligence (VirusTotal) Configuration
GTI_API_KEY = os.environ["GTI_API_KEY"]  # string; VirusTotal API key

# RAG Corpus Configuration
# NOTE: location us-central1 needs allowlist, so us-east4 or other location is recommended
RAG_CORPUS_NAME = os.environ["RAG_CORPUS_NAME"]  # string; full RAG corpus resource name
RAG_SIMILARITY_TOP_K = int(os.environ.get("RAG_SIMILARITY_TOP_K", "10"))  # int; number of docs to retrieve
RAG_DISTANCE_THRESHOLD = float(os.environ.get("RAG_DISTANCE_THRESHOLD", "0.6"))  # float; similarity threshold

service_account_path = Path(CHRONICLE_SERVICE_ACCOUNT_PATH)
service_account_filename = service_account_path.name

secops_siem_tools = McpToolset(
  connection_params=StdioConnectionParams(
    server_params=StdioServerParameters(
      command='uv',
      args=[ "--directory",
              "./mcp-security/server/secops/secops_mcp",
              "run",
              "server.py",
      ],
      env = {
        "CHRONICLE_PROJECT_ID": GCP_PROJECT_ID,  # MCP server expects this name
        "CHRONICLE_CUSTOMER_ID": CHRONICLE_CUSTOMER_ID,
        "CHRONICLE_REGION": CHRONICLE_REGION,
        "SECOPS_SA_PATH": service_account_filename  # MCP server expects this name; packaged app will find file in same dir
      }
    ),
    timeout=60000
  ),
  errlog=None
)

secops_soar_tools = McpToolset(
    connection_params=StdioConnectionParams(
      server_params=StdioServerParameters(
        command='uv',
        args=[ "--directory",
                "./mcp-security/server/secops-soar/secops_soar_mcp",
                "run",
                "server.py",
        ],
        env = {
          "SOAR_URL": SOAR_URL,
          "SOAR_APP_KEY": SOAR_API_KEY  # MCP server expects SOAR_APP_KEY name
       },
    ),
    timeout=60000
  ),
  #tool_set_name="secops_soar_mcp",
  errlog=None
)

gti_tools = McpToolset(
    connection_params=StdioConnectionParams(
      server_params=StdioServerParameters(
        command='uv',
        args=[ "--directory",
                "./mcp-security/server/gti/gti_mcp",
                "run",
                "server.py",
        ],
        env = {
          "VT_APIKEY": GTI_API_KEY,  # MCP server expects VT_APIKEY name
      }
    ),
    timeout=60000
  ),
  errlog=None
)

scc_tools = McpToolset(
    connection_params=StdioConnectionParams(
      server_params=StdioServerParameters(
        command='uv',
        args=[ "--directory",
                "./mcp-security/server/scc",
                "run",
                "scc_mcp.py",
        ],
        env = {},
    ),
    timeout=60000
  ),
  errlog=None
)


# Vertex Search MCP Tool (disabled while researching)
#  Update: this works for search but cannot retrieve the doc *content*
#  vertex_search_tools = McpToolset(
#    connection_params=StdioConnectionParams(
#      server_params=StdioServerParameters(
#        command='python',
#        args=["./mcp-security/server/vertex-search/vertex_search_mcp.py", "--env-file", ".env"],
#        env = {
#          "DATASTORE_PATH": DATASTORE_PATH,
#          "SECOPS_SA_PATH": service_account_filename,  # Pass filename only, will be in same dir
#          "APPLICATION_DEFAULT_CREDENTIALS": os.path.expanduser("~/.config/gcloud/application_default_credentials.json"),
#        }
#      ),
#      timeout=60000
#    ),
#    errlog=None
#  )

ask_vertex_retrieval = VertexAiRagRetrieval(
    name='retrieve_agentic_soc_runbooks',
    description=(
      "Use this tool to retrieve IRPs, Runbooks, Common Steps, and Personas for the Agentic SOC."
    ),
    rag_resources=[
        rag.RagResource(
            rag_corpus=RAG_CORPUS_NAME,
        )
    ],
    similarity_top_k=RAG_SIMILARITY_TOP_K,
    vector_distance_threshold=RAG_DISTANCE_THRESHOLD,
)

root_agent = Agent(
  model="gemini-2.5-flash",  # Fixed: using current model, -exp is deprecated
  name="root_assistant",
  description="Security Operations reasoning agent with access to Agentic SOC MCP tools and runbook search.",
  instruction="""You are a Security Operations assistant with comprehensive access to MCP security tools including RAG-based runbook and documentation retrieval.

YOUR CAPABILITIES:
- Retrieve security Runbooks, IRPs, Common Steps, Procedures, guidelines, and personas using retrieve_agentic_soc_runbooks tool
- Query Chronicle/SIEM for security events and detections
- Manage SOAR cases and incidents
- Access threat intelligence through GTI tools
- Retrieve SCC findings and cloud security posture
- Use list_tools to get full MCP Tool list

WORKFLOW:
1. When users ask about runbooks or procedures, use the retrieve_agentic_soc_runbooks tool to retrieve relevant documentation from the RAG corpus
2. For security investigations, combine runbook guidance with live data from Chronicle, GTI, and SOAR
3. Provide comprehensive responses that integrate procedural knowledge with real-time security data

KEY TOOLS:
- retrieve_agentic_soc_runbooks: Retrieve security procedures and documentation from the RAG corpus
- Chronicle tools: Query SIEM for security events
- SOAR tools: Manage cases and incidents
- GTI tools: Get threat intelligence
- SCC tools: Cloud security findings

Always provide actionable guidance combining documented procedures with live security data.""",
  tools=[
     secops_soar_tools,
     secops_siem_tools,
     gti_tools,
     scc_tools,
     # vertex_search_tools,
     ask_vertex_retrieval,
  ]
)

vertexai.init(
    project=GCP_PROJECT_ID,
    location=GCP_LOCATION,
    staging_bucket=GCP_STAGING_BUCKET,
)

# copy the JSON SA file to the same dir as server.py; ToDo: move to Secret Mgr
shutil.copy(CHRONICLE_SERVICE_ACCOUNT_PATH, "./mcp-security/server/secops/secops_mcp/")
# puts file into agent_engine_dependencies.tar.gz to record state of build (not used as code)
shutil.copy("main.py", "./mcp-security/server/main.txt")
# shutil.copy(SECOPS_SA_PATH, "./mcp-security/server/vertex-search/")  # disabled while researching

def session_service_builder():
  from google.adk.sessions import InMemorySessionService
  return InMemorySessionService()

# Create AdkApp instance
app = AdkApp(
    agent=root_agent,
    # When InMemorySessionService is NOT used in Agentspace: Exception: Cannot send a request, as the client has been closed. (so it MUST be used)
    session_service_builder=session_service_builder,
    enable_tracing=True,
)

remote_app = agent_engines.create(
  app,
  display_name="Agentic SOC Agent Engine",
  requirements=[
    "cloudpickle",
    #"google-adk>=1.15.1",  # _claims_ to fix AttributeError: 'LlmAgent' object has no attribute 'static_instruction'. Did you mean: 'global_instruction' (but no joy)
    "google-adk==1.14.1",  # known-woring
    "google-genai",
    "google-cloud-discoveryengine",
    "google-cloud-aiplatform[agent-engines]",
    "pydantic",
    "python-dotenv",
  ],
  build_options = {"installation_scripts": ["installation_scripts/install.sh"]},
  extra_packages=[
     "mcp-security/server",
     "installation_scripts/install.sh",
  ],
  env_vars={
    "CHRONICLE_PROJECT_ID": GCP_PROJECT_ID,  # MCP servers expect legacy names
    "CHRONICLE_CUSTOMER_ID": CHRONICLE_CUSTOMER_ID,
    "CHRONICLE_REGION": CHRONICLE_REGION,
    "GOOGLE_GENAI_USE_VERTEXAI": GCP_VERTEXAI_ENABLED,  # required for RAG
    "LOCATION": GCP_LOCATION,
    "PROJECT_ID": GCP_PROJECT_ID,
    "RAG_CORPUS": RAG_CORPUS_NAME,
    "SOAR_URL": SOAR_URL,
    "SOAR_APP_KEY": SOAR_API_KEY,
    "VT_APIKEY": GTI_API_KEY,
  }
)

#
# Test agent
#
async def async_test(remote_app):
  user_id = "Dan"
  session = await remote_app.async_create_session(user_id=user_id)
  print(f"session: {session.get('id')}")
  events = []
  async for event in remote_app.async_stream_query(
    user_id=user_id,
    session_id=session.get("id"),
    message="Search RAG Corpus for Malware IRP runbook and get the objective."
    # message="List security rules with ursnif in the name."
    # f" My `project_id is {CHRONICLE_PROJECT_ID} and "
    # f" my customer_id is {CHRONICLE_CUSTOMER_ID} and "
    # f" my region is {CHRONICLE_REGION}.",
  ):
    print(f"event: {event}")
    events.append(event)
  print("after query stream")
  if not events:
      print("No events received from agent!")
  else:
    print(f"Received {len(events)} events")
    for event in events:
       print(f"event: {event}")


asyncio.run(async_test(remote_app))

#
# Delete agent if --delete flag is passed
#
if "--delete" in sys.argv:
    print("\nDeleting agent...")
    remote_app.delete(force=True)
    print("Agent deleted successfully")
else:
    print(f"\nAgent deployed: {remote_app.resource_name}")
