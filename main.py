import asyncio
import os
import sys
from pathlib import Path
import shutil

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.adk.tools import VertexAiSearchTool
from mcp import StdioServerParameters
import vertexai
from vertexai import agent_engines

load_dotenv(os.path.join(os.path.abspath(os.path.dirname(__file__)), ".env"), override=True)

CHRONICLE_CUSTOMER_ID = os.environ["CHRONICLE_CUSTOMER_ID"]
CHRONICLE_PROJECT_ID = os.environ["CHRONICLE_PROJECT_ID"]
CHRONICLE_REGION = os.environ["CHRONICLE_REGION"]
DATASTORE_PATH = os.environ["DATASTORE_PATH"]
LOCATION = os.environ["LOCATION"]
PROJECT_ID = os.environ["PROJECT_ID"]
PROJECT_NUMBER = os.environ["PROJECT_NUMBER"]
SOAR_URL = os.environ["SOAR_URL"]
SOAR_APP_KEY = os.environ["SOAR_APP_KEY"]
STAGING_BUCKET = os.environ["STAGING_BUCKET"]
VT_APIKEY = os.environ["VT_APIKEY"]
SECOPS_SA_PATH = os.environ["SECOPS_SA_PATH"]


service_account_path = Path(SECOPS_SA_PATH)
_ = service_account_path.parent
service_account_filename = service_account_path.name

secops_siem_tools = MCPToolset(
  connection_params=StdioConnectionParams(
    server_params=StdioServerParameters(
      command='uv',
      args=[ "--directory",
              "./mcp-security/server/secops/secops_mcp",
              "run",
              "server.py",
      ],
      env = {
        "CHRONICLE_PROJECT_ID": CHRONICLE_PROJECT_ID,
        "CHRONICLE_CUSTOMER_ID": CHRONICLE_CUSTOMER_ID,
        "CHRONICLE_REGION": CHRONICLE_REGION,
         # packged app will expect this in same dir as server.py
        "SECOPS_SA_PATH": service_account_filename
      }
    ),
    timeout=60
  ),
  errlog=None
)

secops_soar_tools = MCPToolset(
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
          "SOAR_APP_KEY": SOAR_APP_KEY
       },
    ),
    timeout=60
  ),
  #tool_set_name="secops_soar_mcp",
  errlog=None
)

gti_tools = MCPToolset(
    connection_params=StdioConnectionParams(
      server_params=StdioServerParameters(
        command='uv',
        args=[ "--directory",
                "./mcp-security/server/gti/gti_mcp",
                "run",
                "server.py",
        ],
        env = {
          "VT_APIKEY": VT_APIKEY,
      }
    ),
    timeout=60
  ),
  errlog=None
)

scc_tools = MCPToolset(
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
    timeout=600
  ),
  errlog=None
)

# Tool Instantiation
# You MUST provide your datastore ID here.
vertex_search_tool = VertexAiSearchTool(data_store_id=DATASTORE_PATH)

vertex_search_agent = Agent(
  model="gemini-2.5-flash",
  name="vertex_search_agent",
  description="Specialized agent for searching Security Operations runbooks, procedures, and documentation stored in Google Drive.",
  instruction="""You are a specialized documentation search agent for Security Operations.

YOUR ROLE:
- Search through Security Operations runbooks, procedures, and guidelines in Google Drive
- Find relevant step-by-step instructions, best practices, and documented procedures
- Extract specific guidance for security workflows and incident response

SEARCH STRATEGY:
1. Use specific keywords related to the user's security question
2. Look for procedures, runbooks, and guidelines that match the request
3. Provide detailed excerpts from relevant documentation
4. Include document names/sources when possible

RETURN PROTOCOL:
- Always provide your findings in a structured format
- Include relevant quotes and specific steps from the documentation
- If no exact match found, suggest related procedures or general guidance
- End with "Search complete - returning to root agent for additional security tool integration"

Focus on finding actionable documentation that the root agent can combine with live security data.""",
  tools=[
     vertex_search_tool,
  ]
)

root_agent = Agent(
  model="gemini-2.5-flash",
  name="root_assistant",
  description="Security Operations reasoning agent with access to SOAR tools.",
  instruction="""You are a Security Operations assistant with access to MCP security tools and a specialized sub-agent for runbook searches.

DELEGATION RULES:
- When users ask about runbooks, procedures, guidelines, or need to search documentation, delegate to the vertex_search_agent
- When users ask for Chronicle/SIEM queries, threat intelligence, SOAR cases, or SCC findings, handle directly with your MCP tools
- After delegation, review the sub-agent's response and provide additional context or follow-up actions using your security tools if needed

COMMUNICATION PATTERN:
1. If the request involves searching runbooks/procedures: "I'll search our runbooks for that information" → delegate to vertex_search_agent
2. Review sub-agent results and enhance with relevant security tool actions
3. Provide comprehensive response combining runbook guidance with live security data

Use your MCP tools for real-time security operations and delegate documentation searches to ensure complete responses.""",
  tools=[
     secops_soar_tools,
     secops_siem_tools,
     gti_tools,
     scc_tools,
  ],
  sub_agents=[vertex_search_agent]
)

vertexai.init(
    project=PROJECT_ID,
    location=LOCATION,
    staging_bucket=STAGING_BUCKET,
)

# copy the JSON SA file to the same dir as server.py
shutil.copy(SECOPS_SA_PATH, "./mcp-security/server/secops/secops_mcp/")

remote_app = agent_engines.create(
  display_name="Agentic SOC Agent Engine",
  description="Instance of Agent Engine for the Agentic SOC.",
  build_options = {"installation_scripts": ["installation_scripts/install.sh"]},
  extra_packages=[
     "mcp-security/server",
     "installation_scripts/install.sh",
  ],
  agent_engine=root_agent,
  requirements=[
    "cloudpickle==3.1.1",
    "google-cloud-aiplatform[adk,agent_engines]",
    "google-adk",
    "google-genai",
    "pydantic",
    "python-dotenv",
  ],
)

#
# Test agent
#
async def async_test(remote_app):
  session = await remote_app.async_create_session(user_id="D")
  print(f"session: {session}")
  async for event in remote_app.async_stream_query(
    user_id="D",
    session_id=session.get("id"),
    message="I need to investigate a potential malware incident. Please search our runbooks for incident response procedures for malware analysis, then use Chronicle to search for any recent ursnif-related security rules or detections."
      #f" My `project_id is {CHRONICLE_PROJECT_ID} and "
      #f" my customer_id is {CHRONICLE_CUSTOMER_ID} and "
      #f" my region is {CHRONICLE_REGION}.",
  ):
    print(f"event: {event}")
  print("after query stream")

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
