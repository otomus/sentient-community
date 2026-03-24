import json

def explain_quantum_computing() -> str:
    """
    Explains the principles and applications of quantum computing in a simple way.
    """
    try:
        explanation = """
Quantum computing is a type of computing that uses quantum-mechanical phenomena, such as superposition and entanglement, to perform operations on data. Unlike classical computers, which use bits that are either 0 or 1, quantum computers use quantum bits, or qubits, which can be 0, 1, or both at the same time. This allows quantum computers to perform certain calculations much faster than classical computers.

Quantum computing has many potential applications, including cryptography, drug discovery, and artificial intelligence. For example, quantum computers could be used to break encryption much faster than classical computers, which could have significant implications for cybersecurity. They could also be used to simulate the behavior of molecules and materials, which could help in the development of new drugs and materials.
"""
        return json.dumps({"explanation": explanation})
    except Exception as e:
        return json.dumps({"error": str(e)})