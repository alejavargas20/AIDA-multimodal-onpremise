def example_echo_tool(payload: dict):
    text = payload.get("text", "")
    return {"echo": text}
