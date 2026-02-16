# mcp/__init__.py
# from typing import Callable, Dict
# import logging

# logger = logging.getLogger("mcp")
# logger.setLevel(logging.INFO)
# handler = logging.StreamHandler()
# handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
# logger.addHandler(handler)

# _TOOL_REGISTRY: Dict[str, Callable] = {}

# def register_tool(name: str):
#     def decorator(fn):
#         _TOOL_REGISTRY[name] = fn
#         logger.info(f"Registered tool: {name}")
#         return fn
#     return decorator

# def get_tool(name: str):
#     return _TOOL_REGISTRY.get(name)

# def list_tools():
#     return list(_TOOL_REGISTRY.keys())


# mcp/__init__.py

import logging

__version__ = "0.1.0"

logger = logging.getLogger("mcp")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s | MCP | %(levelname)s | %(message)s"
)
handler.setFormatter(formatter)

if not logger.handlers:
    logger.addHandler(handler)

