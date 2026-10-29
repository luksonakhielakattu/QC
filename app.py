import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, Pauli, state_fidelity

st.set_page_config(
    page_title="Shor 9-Qubit Error Correction",
    page_icon="⚛️",
    layout="wide"
)

# -------------------- PAGE DESIGN --------------------

st.markdown("""
<style>
.main-title {
    font-size: 32px;
    font-weight: 750;
    color: #343746;
}
.subtitle {
    font-size: 16px;
    color: #666;
}
div.stButton > button[kind="primary"] {
    background-color: #ff4b4b;
    color: white;
    border-radius: 8px;
    height: 45px;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# -------------------- QUANTUM STABILIZERS --------------------

STABILIZERS = [
    ("Z0Z1", {0: "Z", 1: "Z"}),
    ("Z1Z2", {1: "Z", 2: "Z"}),
    ("Z3Z4", {3: "Z", 4: "Z"}),
    ("Z4Z5", {4: "Z", 5: "Z"}),
    ("Z6Z7", {6: "Z", 7: "Z"}),
    ("Z7Z8", {7: "Z", 8: "Z"}),
    ("X0X1X2X3X4X5", {i: "X" for i in range(6)}),
    ("X3X4X5X6X7X8", {i: "X" for i in range(3, 9)}),
]


def make_pauli(operations):
    label = ["I"] * 9
    for qubit, operation in operations.items():
        label[8 - qubit] = operation
    return Pauli("".join(label))


def prepare_input(qc, state):
    if state == "|1⟩":
        qc.x(0)
    elif state == "|+⟩":
        qc.h(0)
    elif state == "|−⟩":
        qc.x(0)
        qc.h(0)
    elif state == "|+i⟩":
        qc.h(0)
        qc.s(0)
    elif state == "|−i⟩":
        qc.h(0)
        qc.sdg(0)


def encode_shor(qc):
    # Spread the logical information across three blocks.
    qc.cx(0, 3)
    qc.cx(0, 6)

    # Phase-flip encoding.
    qc.h(0)
    qc.h(3)
    qc.h(6)

    # Bit-flip encoding inside each block.
    for leader in [0, 3, 6]:
        qc.cx(leader, leader + 1)
        qc.cx(leader, leader + 2)


def calculate_syndrome(statevector):
    syndrome = ""

    for _, operations in STABILIZERS:
        expectation = statevector.expectation_value(
            make_pauli(operations)
        ).real

        syndrome += "0" if expectation > 0 else "1"

    return syndrome


def theoretical_syndrome(qubit, error):
    bits = []

    for _, operations in STABILIZERS:
        stabilizer_pauli = operations.get(qubit, "I")

        if stabilizer_pauli == "I":
            bits.append("0")
        elif stabilizer_pauli == error:
            bits.append("0")
        else:
            bits.append("1")

    return "".join(bits)


def build_decoder():
    decoder = {}

    for qubit in range(9):
        for error in ["X", "Y", "Z"]:
            syndrome = theoretical_syndrome(qubit, error)
            decoder.setdefault(syndrome, (qubit, error))

    return decoder


DECODER = build_decoder()


def simulate(input_state, error_qubit, error_type):
    qc = QuantumCircuit(9)

    prepare_input(qc, input_state)
    encode_shor(qc)

    original = Statevector.from_instruction(qc)

    # Inject the selected single-qubit error.
    getattr(qc, error_type.lower())(error_qubit)

    damaged = Statevector.from_instruction(qc)
    syndrome = calculate_syndrome(damaged)

    recovery = None

    if syndrome != "00000000":
        recovery = DECODER.get(syndrome)

        if recovery:
            recovery_qubit, recovery_type = recovery
            getattr(qc, recovery_type.lower())(recovery_qubit)

    recovered = Statevector.from_instruction(qc)
    fidelity = state_fidelity(original, recovered)

    return qc, syndrome, recovery, fidelity


# -------------------- SIDEBAR --------------------

with st.sidebar:
    st.markdown("## ⚙️ Experiment Configuration")
    st.caption("Shor's 9-Qubit Quantum Code")

    input_state = st.selectbox(
        "Input quantum state",
        ["|0⟩", "|1⟩", "|+⟩", "|−⟩", "|+i⟩", "|−i⟩"]
    )

    error_qubit = st.selectbox(
        "Error location",
        list(range(9)),
        format_func=lambda q: f"Qubit Q{q + 1}"
    )

    error_type = st.selectbox(
        "Single-qubit error",
        ["X", "Y", "Z"]
    )

    st.divider()
    st.markdown("### Error types")
    st.write("**X:** Bit-flip error")
    st.write("**Y:** Bit and phase-flip error")
    st.write("**Z:** Phase-flip error")

    st.info("Select an input state and an error, then press Run Simulation.")


# -------------------- MAIN INTERFACE --------------------

st.markdown(
    '<div class="main-title">⚛️ Shor 9-Qubit Error Correction</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">Encode a logical qubit, inject a Pauli error, '
    'inspect the syndrome and evaluate quantum-state recovery.</div>',
    unsafe_allow_html=True
)

st.divider()

st.markdown("## 1. Configure the experiment")

col1, col2, col3 = st.columns(3)
col1.metric("Logical qubits", "1")
col2.metric("Physical qubits", "9")
col3.metric("Possible single-qubit errors", "27")

st.write(
    f"**Input state:** {input_state}  |  "
    f"**Selected error:** {error_type} on Q{error_qubit + 1}"
)

st.markdown("## 2. Shor Encoding and Error Circuit")

preview = QuantumCircuit(9)
prepare_input(preview, input_state)
encode_shor(preview)
getattr(preview, error_type.lower())(error_qubit)

try:
    figure = preview.draw(output="mpl", fold=-1, style="clifford")
    st.pyplot(figure, use_container_width=True)
    plt.close(figure)
except Exception:
    st.code(str(preview.draw(output="text")))

st.caption(
    "The circuit displays input preparation, Shor encoding and error injection. "
    "Syndrome extraction is simulated from stabilizer expectations below."
)

st.markdown("## 3. Run the Quantum Simulation")

if st.button("▶ Run Simulation", type="primary", use_container_width=True):
    qc, syndrome, recovery, fidelity = simulate(
        input_state, error_qubit, error_type
    )

    st.session_state["single_result"] = {
        "syndrome": syndrome,
        "recovery": recovery,
        "fidelity": fidelity,
        "error_qubit": error_qubit,
        "error_type": error_type,
        "input_state": input_state,
    }

if "single_result" in st.session_state:
    result = st.session_state["single_result"]

    st.markdown("## 4. Simulation Results")

    a, b, c = st.columns(3)
    a.metric(
        "Injected error",
        f"{result['error_type']} on Q{result['error_qubit'] + 1}"
    )
    b.metric("Measured syndrome", result["syndrome"])
    c.metric("Recovery fidelity", f"{result['fidelity']:.6f}")

    if result["recovery"]:
        rq, rt = result["recovery"]
        st.write(f"**Recovery operation:** Apply {rt} to Q{rq + 1}.")
    else:
        st.write("**Recovery operation:** No correction selected.")

    if result["fidelity"] > 0.999999:
        st.success("The original encoded state was recovered in simulation.")
    else:
        st.error("Recovery was not successful for this case.")

    syndrome_table = []

    for (name, _), bit in zip(STABILIZERS, result["syndrome"]):
        syndrome_table.append({
            "Stabilizer": name,
            "Syndrome bit": bit,
            "Interpretation": "Error detected" if bit == "1"
            else "No anticommutation detected"
        })

    st.markdown("### Stabilizer Syndrome")
    st.dataframe(
        pd.DataFrame(syndrome_table),
        use_container_width=True,
        hide_index=True
    )

st.divider()

# -------------------- ALL 27 TEST CASES --------------------

st.markdown("## 5. Test All 27 Single-Qubit Errors")

st.write(
    "Run X, Y and Z errors on each of the nine physical qubits "
    "and inspect the syndrome, recovery operation and fidelity."
)

if st.button("▶ Run All 27 Error Cases", use_container_width=True):
    rows = []

    progress = st.progress(0)
    total = 27
    count = 0

    for qubit in range(9):
        for error in ["X", "Y", "Z"]:
            _, syndrome, recovery, fidelity = simulate(
                input_state, qubit, error
            )

            rows.append({
                "Qubit": f"Q{qubit + 1}",
                "Error": error,
                "Syndrome": syndrome,
                "Recovery": (
                    f"{recovery[1]} on Q{recovery[0] + 1}"
                    if recovery else "Not identified"
                ),
                "Fidelity": round(fidelity, 8),
                "Corrected": fidelity > 0.999999,
            })

            count += 1
            progress.progress(count / total)

    results = pd.DataFrame(rows)
    st.session_state["all_results"] = results

if "all_results" in st.session_state:
    results = st.session_state["all_results"]

    correct_count = int(results["Corrected"].sum())

    a, b, c = st.columns(3)
    a.metric("Total test cases", len(results))
    b.metric("Successfully recovered", f"{correct_count} / 27")
    c.metric("Failed cases", 27 - correct_count)

    st.dataframe(results, use_container_width=True, hide_index=True)

    st.markdown("### Recovery Results Chart")

    chart_data = results.groupby("Error")["Corrected"].sum()
    st.bar_chart(chart_data)

    st.download_button(
        "⬇ Download Test Results (CSV)",
        data=results.to_csv(index=False).encode("utf-8"),
        file_name="shor_9_qubit_results.csv",
        mime="text/csv",
        use_container_width=True
    )

st.divider()

st.markdown("### 6. About the Simulation")
st.info(
    "This educational version calculates stabilizer syndromes using ideal "
    "statevectors. It does not yet implement ancilla-based syndrome extraction "
    "with measurement gates or simulate hardware noise. Verify all 27 cases "
    "before using the results as evidence of successful correction."
)