"""ADK research-assistant capstone package.

`from . import agent` exposes `agent.root_agent` for the `adk` CLIs
(adk run / adk web / adk api_server / adk eval).
"""
from . import agent
from .agent import root_agent, build_root_agent

__all__ = ["agent", "root_agent", "build_root_agent"]
