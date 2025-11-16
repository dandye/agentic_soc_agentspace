"""
SOC Agent Tier 1 Analyst Module

This module provides a Security Operations Agent configured with a Tier 1 SOC Analyst persona,
specialized for alert triage, initial investigation, and escalation of security incidents.

The Tier 1 agent focuses on:
- Alert monitoring and triage
- Basic IOC enrichment
- Case management in SOAR
- Escalation to Tier 2/3 analysts

Usage:
    # Standard ADK import pattern
    from soc_agent_tier1 import agent
    my_agent = agent.root_agent

    # Or create a fresh agent
    from soc_agent_tier1 import create_agent
    my_agent = create_agent()
"""

# Import the agent module (ADK standard pattern)
from . import agent

# Also expose the main functions for convenience
from .agent import create_agent, root_agent


__version__ = "1.0.0"

__all__ = [
    "agent",
    "create_agent",
    "root_agent",
]
