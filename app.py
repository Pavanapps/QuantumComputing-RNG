# app.py

from flask import Flask, render_template, request, jsonify
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
import math
import datetime

# Optional IBM Quantum backend
USE_IBM = True
try:
    from qiskit_ibm_runtime import QiskitRuntimeService
except:
    USE_IBM = False

app = Flask(__name__)


# -----------------------------------
# Utility Functions
# -----------------------------------

def compute_metrics(counts):
    total = sum(counts.values())

    expectation = 0
    variance = 0

    for state, count in counts.items():
        value = int(state, 2)
        prob = count / total
        expectation += value * prob

    for state, count in counts.items():
        value = int(state, 2)
        prob = count / total
        variance += prob * ((value - expectation) ** 2)

    return round(expectation, 4), round(variance, 4)


def shannon_entropy(counts):
    total = sum(counts.values())
    entropy = 0

    for count in counts.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)

    return round(entropy, 4)


def build_quantum_circuit(bits):
    qc = QuantumCircuit(bits, bits)

    for i in range(bits):
        qc.h(i)

    qc.measure(range(bits), range(bits))
    return qc


# -----------------------------------
# Quantum Execution
# -----------------------------------

def run_simulator(bits, shots):
    qc = build_quantum_circuit(bits)

    simulator = AerSimulator()
    job = simulator.run(qc, shots=shots)
    result = job.result()

    return result.get_counts()


def run_real_hardware(bits, shots):
    if not USE_IBM:
        return run_simulator(bits, shots)

    try:
        qc = build_quantum_circuit(bits)

        service = QiskitRuntimeService()
        backend = service.least_busy(simulator=False, operational=True)

        job = backend.run(qc, shots=shots)
        result = job.result()

        return result.get_counts()

    except:
        return run_simulator(bits, shots)


# -----------------------------------
# Main RNG Logic
# -----------------------------------

def generate_qrng(bits, shots, backend):

    if backend == "real":
        counts = run_real_hardware(bits, shots)
        used_backend = "IBM Hardware" if USE_IBM else "Simulator Fallback"
    else:
        counts = run_simulator(bits, shots)
        used_backend = "Simulator"

    bitstring = max(counts, key=counts.get)
    decimal = int(bitstring, 2)

    expectation, variance = compute_metrics(counts)
    entropy = shannon_entropy(counts)

    hex_value = hex(decimal).upper()

    return {
        "bitstring": bitstring,
        "decimal": decimal,
        "hex": hex_value,
        "counts": counts,
        "expectation": expectation,
        "variance": variance,
        "entropy": entropy,
        "backend_used": used_backend,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


# -----------------------------------
# Routes
# -----------------------------------

@app.route('/')
def home():
    return render_template("index.html")


@app.route('/generate', methods=['POST'])
def generate():

    try:
        data = request.get_json()

        bits = int(data.get("bits", 4))
        shots = int(data.get("shots", 100))
        backend = data.get("backend", "simulator")

        # Safety Limits
        if bits < 1:
            bits = 1
        if bits > 16:
            bits = 16

        if shots < 1:
            shots = 1
        if shots > 5000:
            shots = 5000

        result = generate_qrng(bits, shots, backend)

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


# -----------------------------------
# Start
# -----------------------------------

if __name__ == "__main__":
    app.run(debug=True)
