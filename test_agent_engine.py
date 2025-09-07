import asyncio
import os

from dotenv import load_dotenv
import vertexai
from vertexai import agent_engines


BASEDIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASEDIR, ".env"))

LOCATION = os.environ['LOCATION']
PROJECT = os.environ['PROJECT_ID']
PROJECT_NUMBER = os.environ['PROJECT_NUMBER']
REASONING_ENGINE = os.environ['REASONING_ENGINE']

vertexai.init(
    project=PROJECT,
    location=LOCATION,
    staging_bucket=os.environ['STAGING_BUCKET'],
)

async def main():
  remote_app = agent_engines.get(
    f"projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{REASONING_ENGINE}"
  )
  session = await remote_app.async_create_session(user_id="D")
  print(f"session: {session}")
  async for event in remote_app.async_stream_query(
    user_id="D",
    session_id=session.get("id"),
    message="List SOAR Cases",
  ):
    print(f"event: {event}")
  print("after query stream")

if __name__ == "__main__":
  asyncio.run(main())
