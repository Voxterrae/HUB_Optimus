import asyncio
import os

from agent_framework.azure import AzureAIClient
from azure.ai.agentserver.agentframework import from_agent_framework
from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv

try:
    from .tracing import setup_tracing
except ImportError:
    # Fallback for when running as a script
    from tracing import setup_tracing


def _get_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


async def main() -> None:
    load_dotenv(override=True)
    
    # Initialize tracing
    tracer = setup_tracing("hub-optimus-agent")
    if tracer:
        print("OpenTelemetry tracing initialized")

    project_endpoint = _get_env("FOUNDRY_PROJECT_ENDPOINT")
    deployment_name = _get_env("FOUNDRY_MODEL_DEPLOYMENT_NAME")

    agent_name = os.getenv("AGENT_NAME", "HUB-Optimus-Agent")
    instructions = os.getenv(
        "AGENT_INSTRUCTIONS",
        "You are HUB_Optimus, a careful, integrity-first simulation assistant. "
        "Help users explore scenarios, clarify incentives, and evaluate verification steps."
    )

    async with DefaultAzureCredential() as credential:
        async with (
            AzureAIClient(
                project_endpoint=project_endpoint,
                model_deployment_name=deployment_name,
                credential=credential,
            ).create_agent(
                name=agent_name,
                instructions=instructions,
            ) as agent
        ):
            await from_agent_framework(agent).run_async()


if __name__ == "__main__":
    asyncio.run(main())
