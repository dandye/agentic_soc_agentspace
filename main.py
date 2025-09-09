import asyncio
import os
import sys

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
import vertexai
from vertexai import agent_engines

load_dotenv(os.path.join(os.path.abspath(os.path.dirname(__file__)), ".env"))

CHRONICLE_CUSTOMER_ID = os.environ["CHRONICLE_CUSTOMER_ID"]
CHRONICLE_PROJECT_ID = os.environ["CHRONICLE_PROJECT_ID"]
CHRONICLE_REGION = os.environ["CHRONICLE_CUSTOMER_ID"]
LOCATION = os.environ["LOCATION"]
PROJECT_ID = os.environ["PROJECT_ID"]
PROJECT_NUMBER = os.environ["PROJECT_NUMBER"]
SOAR_URL = os.environ["SOAR_URL"]
SOAR_APP_KEY = os.environ["SOAR_APP_KEY"]
STAGING_BUCKET = os.environ["STAGING_BUCKET"]
VT_APIKEY = os.environ["VT_APIKEY"]

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

root_agent = Agent(
  model="gemini-2.5-flash",
  name="root_assistant",
  description="Security Operations reasoning agent with access to SOAR tools.",
  instruction="Use the available MCP tools and reasoning to fulfil user requests.",
  tools=[
     secops_soar_tools,
     secops_siem_tools,
     gti_tools,
     scc_tools,
  ]
)

vertexai.init(
    project=PROJECT_ID,
    location=LOCATION,
    staging_bucket=STAGING_BUCKET,
)

remote_app = agent_engines.create(
  display_name="SOC Agent",
  description="Simple agent plus google search tool.",
  build_options = {"installation_scripts": ["installation_scripts/install.sh"]},
  extra_packages=["mcp-security/server", "installation_scripts/install.sh"],
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
    message="List the MCP Tools and then use the list_cases tool to get SOAR Cases.",
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