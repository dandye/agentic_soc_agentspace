import asyncio
import os

os.environ['GRPC_VERBOSITY'] = 'INFO'
#os.environ['GRPC_TRACE'] = 'all'
from dotenv import load_dotenv
import vertexai
from vertexai import agent_engines


BASEDIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASEDIR, ".env"), override=True)

LOCATION = os.environ['GCP_LOCATION']
PROJECT = os.environ['GCP_PROJECT_ID']
PROJECT_NUMBER = os.environ['GCP_PROJECT_NUMBER']
# Extract engine ID from full resource name format
# Format: projects/{num}/locations/{loc}/reasoningEngines/{id}
AGENT_ENGINE_RESOURCE_NAME = os.environ['AGENT_ENGINE_RESOURCE_NAME']
REASONING_ENGINE = AGENT_ENGINE_RESOURCE_NAME.split('/')[-1]

vertexai.init(
    project=PROJECT,
    location=LOCATION,
    staging_bucket=os.environ['GCP_STAGING_BUCKET'],
)

async def main():
  remote_app = agent_engines.get(
    f"projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{REASONING_ENGINE}"
  )


  #session = await remote_app.async_create_session(user_id="D")
  from google.api_core import exceptions

  try:
      session = await remote_app.async_create_session(user_id="D")
  except exceptions.FailedPrecondition as e:
      print(f"Full error message: {e.message}")
      print(f"Error details: {e.details}")
      print(f"Error cause: {e.__cause__}")
      print(f"Debug string: {e.debug_error_string}")
      # Also try:
      if hasattr(e, '_details'):
          print(f"Internal details: {e._details}")
      raise

  print(f"session: {session}")

  query = "List the available MCP Tools"

  # Try a simple query first
  print(f"Sending query: {query}")
  events = []
  async for event in remote_app.async_stream_query(
    user_id="D",
    session_id=session.get("id"),
    message=query,
  ):
    print(f"event: {event}")
    events.append(event)

  if not events:
    print("No events received from agent!")
  else:
    print(f"Received {len(events)} events")

  print("after query stream")

if __name__ == "__main__":
  asyncio.run(main())
