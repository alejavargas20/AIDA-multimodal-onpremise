from orchestrator.graph import orchestrator_app

initial_state = {
    "user_id": "123",
    "session_id": "abc",
    "input_type": "pdf",
    "raw_input": "Explicame que es la mora",
    "user_profile": "no_tecnico",
}
print("INPUT")
print(initial_state)

output = orchestrator_app.invoke(initial_state)
print("\n")
print("OUTPUT")
print(output["final_text"])
print("------------------------")
print("\n")
