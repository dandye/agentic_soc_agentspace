"""
SOC Agent CTI Researcher Module

This module provides a Cyber Threat Intelligence (CTI) Researcher agent configured with
specific persona, responsibilities, and MCP tools for threat intelligence operations.

The CTI Researcher focuses on:
- Proactive threat discovery and analysis
- Threat actor tracking and campaign investigation
- Intelligence production and dissemination
- IOC and TTP analysis with MITRE ATT&CK mapping

Usage:
    # Standard ADK import pattern
    from soc_agent_cti import agent
    my_agent = agent.root_agent

    # Or create a fresh agent
    from soc_agent_cti import create_agent
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
