from flask import Flask, render_template, request, jsonify
from qiskit import QuantumCircuit
from qiskit_aer import Aer
from qiskit.quantum_info import Statevector
from qiskit.visualization import plot_bloch_multivector

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import os
import time

# IBM backend optional
USE_IBM = False

try:
    from qiskit_ibm_runtime import QiskitRuntimeService
    USE_IBM = True
except:
    pass

app = Flask(__name__)


def generate_qrng(n_bits, shots, use_real=False):

    qc = QuantumCircuit(n_bits, n_bits)

    for i in range(n_bits):
        qc.h(i)

    bloch_path = None

    # Bloch sphere only for 1 qubit
    if n_bits == 1:
        try:
            state = Statevector.from_instruction(qc)

            fig = plot_bloch_multivector(state)

            os.makedirs("static", exist_ok=True)

            bloch_path = f"static/bloch_{int(time.time())}.png"

            fig.savefig(bloch_path, bbox_inches="tight")
            plt.close(fig)

        except Exception as e:
            print("Bloch Error:", e)
            bloch_path = None

    # Measurement
    qc.measure(range(n_bits), range(n_bits))

    # Backend run
    if use_real and USE_IBM:
        service = QiskitRuntimeService()
        backend = service.least_busy(simulator=False)

        job = backend.run(qc, shots=shots)
        result = job.result()
        counts = result.get_counts()

    else:
        simulator = Aer.get_backend("qasm_simulator")
        result = simulator.run(qc, shots=shots).result()
        counts = result.get_counts()

    bitstring = max(counts, key=counts.get)
    decimal = int(bitstring, 2)

    return counts, bitstring, decimal, bloch_path


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
        variance += prob * (value - expectation) ** 2

    return round(expectation, 4), round(variance, 4)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():

    data = request.json

    n_bits = int(data["bits"])
    shots = int(data["shots"])
    backend_type = data["backend"]

    use_real = backend_type == "real"

    counts, bitstring, decimal, bloch_path = generate_qrng(
        n_bits, shots, use_real
    )

    expectation, variance = compute_metrics(counts)

    return jsonify({
        "bitstring": bitstring,
        "decimal": decimal,
        "counts": counts,
        "expectation": expectation,
        "variance": variance,
        "bloch": bloch_path
    })


if __name__ == "__main__":
    app.run(debug=True)
