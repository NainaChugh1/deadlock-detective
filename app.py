import io
import json
from datetime import datetime

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="Deadlock Detective",
    page_icon="🕵️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stApp { background: #0b1020; color: #e8edf7; }
    [data-testid="stSidebar"] { background: #11182b; }
    .block-container { padding-top: 1.5rem; max-width: 1500px; }
    .hero { padding: 1.2rem 1.4rem; border: 1px solid #273451; border-radius: 16px;
            background: linear-gradient(120deg,#121b31,#101827); margin-bottom: 1rem; }
    .eyebrow { color: #f4a261; letter-spacing: .16em; font-size: .75rem; font-weight: 700; }
    .hero h1 { margin: .25rem 0; color: #f4f7ff; }
    .muted { color: #9ba9c4; }
    div[data-testid="stMetric"] { background: #121b2e; border: 1px solid #263653;
        padding: 12px; border-radius: 12px; }
    .stButton > button { border-radius: 9px; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <div class="eyebrow">OS INVESTIGATION TOOL · CSE316</div>
  <h1>🕵️ DEADLOCK DETECTIVE</h1>
  <div class="muted">Deadlock analysis · Resource Allocation Graph · Banker's Algorithm · Recovery</div>
</div>
""", unsafe_allow_html=True)

PRESETS = {
    "Classic Deadlock": {
        "resources": ["R0", "R1"],
        "total": [1, 1],
        "processes": ["P0", "P1"],
        "allocation": [[1, 0], [0, 1]],
        "max_demand": [[1, 1], [1, 1]],
        "requests": [[0, 1], [1, 0]],
    },
    "Safe State": {
        "resources": ["R0", "R1", "R2"],
        "total": [10, 5, 7],
        "processes": ["P0", "P1", "P2", "P3", "P4"],
        "allocation": [[0, 1, 0], [2, 0, 0], [3, 0, 2], [2, 1, 1], [0, 0, 2]],
        "max_demand": [[7, 5, 3], [3, 2, 2], [9, 0, 2], [2, 2, 2], [4, 3, 3]],
        "requests": [[0, 0, 0] for _ in range(5)],
    },
    "Dining Philosophers": {
        "resources": ["Fork0", "Fork1", "Fork2", "Fork3", "Fork4"],
        "total": [1, 1, 1, 1, 1],
        "processes": ["P0", "P1", "P2", "P3", "P4"],
        "allocation": [[1, 0, 0, 0, 0], [0, 1, 0, 0, 0], [0, 0, 1, 0, 0], [0, 0, 0, 1, 0], [0, 0, 0, 0, 1]],
        "max_demand": [[1, 1, 0, 0, 0], [0, 1, 1, 0, 0], [0, 0, 1, 1, 0], [0, 0, 0, 1, 1], [1, 0, 0, 0, 1]],
        "requests": [[0, 1, 0, 0, 0], [0, 0, 1, 0, 0], [0, 0, 0, 1, 0], [0, 0, 0, 0, 1], [1, 0, 0, 0, 0]],
    },
    "Unsafe-but-No-Deadlock": {
        "resources": ["R0", "R1"],
        "total": [3, 2],
        "processes": ["P0", "P1"],
        "allocation": [[1, 0], [0, 1]],
        "max_demand": [[3, 2], [2, 2]],
        "requests": [[0, 0], [0, 0]],
    },
}


def bankers(processes, allocation, max_demand, available):
    n = len(processes)
    m = len(available)
    need = [[max_demand[i][j] - allocation[i][j] for j in range(m)] for i in range(n)]
    work = available[:]
    finish = [False] * n
    sequence = []
    trace = [f"Initial Work = {work}"]
    while len(sequence) < n:
        found = False
        for i, p in enumerate(processes):
            if not finish[i] and all(need[i][j] <= work[j] for j in range(m)):
                before = work[:]
                work = [work[j] + allocation[i][j] for j in range(m)]
                finish[i] = True
                sequence.append(p)
                trace.append(f"{p}: Need {need[i]} ≤ Work {before} → can finish; release Allocation {allocation[i]}; Work becomes {work}")
                found = True
        if not found:
            blocked = [processes[i] for i in range(n) if not finish[i]]
            trace.append(f"No unfinished process can proceed. Remaining processes: {', '.join(blocked)}")
            break
    return all(finish), sequence, need, trace, [processes[i] for i in range(n) if not finish[i]]


def find_cycles(graph):
    """Return simple directed cycles, canonicalized and limited for readable display."""
    try:
        cycles = list(nx.simple_cycles(graph))
        return cycles[:10]
    except Exception:
        return []


def build_rag(processes, resources, allocation, requests):
    graph = nx.DiGraph()
    for p in processes:
        graph.add_node(p, kind="process")
    for r in resources:
        graph.add_node(r, kind="resource")
    for i, p in enumerate(processes):
        for j, r in enumerate(resources):
            if allocation[i][j] > 0:
                graph.add_edge(r, p, edge_kind="assignment", amount=allocation[i][j])
            if requests[i][j] > 0:
                graph.add_edge(p, r, edge_kind="request", amount=requests[i][j])
    return graph


def draw_graph(graph, deadlocked=None):
    deadlocked = set(deadlocked or [])
    fig, ax = plt.subplots(figsize=(10, 5.5))
    fig.patch.set_facecolor("#0f1728")
    ax.set_facecolor("#0f1728")
    processes = [n for n, d in graph.nodes(data=True) if d.get("kind") == "process"]
    resources = [n for n, d in graph.nodes(data=True) if d.get("kind") == "resource"]
    pos = {}
    for i, n in enumerate(processes):
        pos[n] = (0, -i)
    for i, n in enumerate(resources):
        pos[n] = (2.4, -i * (max(1, len(processes)-1) / max(1, len(resources)-1)) if len(resources) > 1 else -max(0, len(processes)-1)/2)
    process_colors = ["#e63946" if n in deadlocked else "#4895ef" for n in processes]
    nx.draw_networkx_nodes(graph, pos, nodelist=processes, node_shape="o", node_color=process_colors,
                           node_size=1400, edgecolors="#dbeafe", linewidths=1.1, ax=ax)
    nx.draw_networkx_nodes(graph, pos, nodelist=resources, node_shape="s", node_color="#f4a261",
                           node_size=1400, edgecolors="#ffedd5", linewidths=1.1, ax=ax)
    nx.draw_networkx_labels(graph, pos, font_size=9, font_color="#101827", font_weight="bold", ax=ax)
    assignment = [(u, v) for u, v, d in graph.edges(data=True) if d.get("edge_kind") == "assignment"]
    request = [(u, v) for u, v, d in graph.edges(data=True) if d.get("edge_kind") == "request"]
    nx.draw_networkx_edges(graph, pos, edgelist=assignment, arrows=True, arrowstyle="-|>", arrowsize=18,
                           width=2, edge_color="#cbd5e1", connectionstyle="arc3,rad=0.04", ax=ax)
    nx.draw_networkx_edges(graph, pos, edgelist=request, arrows=True, arrowstyle="-|>", arrowsize=18,
                           width=2, style="dashed", edge_color="#fb923c", connectionstyle="arc3,rad=0.08", ax=ax)
    labels = {(u, v): str(d.get("amount", "")) for u, v, d in graph.edges(data=True)}
    nx.draw_networkx_edge_labels(graph, pos, edge_labels=labels, font_color="#f8fafc", font_size=8, ax=ax)
    ax.set_title("Resource Allocation Graph", color="#f8fafc", fontsize=14, pad=15)
    ax.text(0.02, -0.02, "● Process    ■ Resource    Solid: allocated    Dashed: requested",
            transform=ax.transAxes, color="#cbd5e1", fontsize=9)
    ax.axis("off")
    fig.tight_layout()
    return fig


def recovery_suggestions(blocked, resources, allocation, requests, processes):
    if not blocked:
        return [
            ("No recovery required", "The system has a safe sequence under the current snapshot.", "None")
        ]
    target = blocked[0]
    idx = processes.index(target)
    held = [(resources[j], allocation[idx][j]) for j in range(len(resources)) if allocation[idx][j] > 0]
    held_text = ", ".join(f"{r} × {amount}" for r, amount in held) or "no currently allocated resources"
    return [
        ("Process termination", f"Consider terminating {target}; it currently holds {held_text}. This can release its allocations, but discards its work.", "Medium / workload-dependent"),
        ("Resource preemption", f"Assess whether a resource held by {target} can safely be reclaimed and reassigned. Preemption may require rollback and is not valid for every resource.", "Context-dependent"),
        ("Rollback to checkpoint", f"If checkpoints exist, restore {target} to a prior safe state and retry with a different resource order.", "Depends on checkpoint cost"),
    ]


def make_report(data):
    safe, sequence, need, trace, blocked = bankers(
        data["processes"], data["allocation"], data["max_demand"], data["available"]
    )
    graph = build_rag(data["processes"], data["resources"], data["allocation"], data["requests"])
    cycles = find_cycles(graph)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "case": data["case"],
        "processes": data["processes"],
        "resources": data["resources"],
        "total": data["total"],
        "allocation": data["allocation"],
        "max_demand": data["max_demand"],
        "need": need,
        "available": data["available"],
        "bankers_safe": safe,
        "safe_sequence": sequence,
        "unfinished_processes": blocked,
        "bankers_trace": trace,
        "rag_cycles": cycles,
        "cycle_note": "A cycle in a resource-allocation graph is not always proof of deadlock when resource types have multiple instances. Banker's Algorithm here reports whether the snapshot is safe.",
        "recovery_suggestions": recovery_suggestions(blocked, data["resources"], data["allocation"], data["requests"], data["processes"]),
    }


with st.sidebar:
    st.markdown("## Case configuration")
    scenario = st.selectbox("Load a preset", list(PRESETS.keys()))
    st.caption("Choose a preset to initialize the editable tables below.")
    st.markdown("---")
    st.markdown("**Legend**")
    st.markdown("🔵 Process node")
    st.markdown("🟧 Resource node")
    st.markdown("Solid arrow: resource allocated")
    st.markdown("Dashed arrow: process request")
    st.markdown("---")
    st.caption("Educational simulator. It analyzes a modelled snapshot; it does not inspect or control your computer's operating system.")

preset = PRESETS[scenario]
st.subheader("01 / Setup")
st.caption("Preset values are loaded as a starting point. Edit the tables to investigate your own case.")

# Session state is reset when the selected preset changes.
if "last_scenario" not in st.session_state or st.session_state.last_scenario != scenario:
    st.session_state.last_scenario = scenario
    st.session_state.total_df = pd.DataFrame([preset["total"]], columns=preset["resources"], index=["Total instances"])
    st.session_state.alloc_df = pd.DataFrame(preset["allocation"], columns=preset["resources"], index=preset["processes"])
    st.session_state.max_df = pd.DataFrame(preset["max_demand"], columns=preset["resources"], index=preset["processes"])
    st.session_state.req_df = pd.DataFrame(preset["requests"], columns=preset["resources"], index=preset["processes"])

processes = preset["processes"]
resources = preset["resources"]

left, right = st.columns([1, 1])
with left:
    st.markdown("**Total resource instances**")
    total_df = st.data_editor(st.session_state.total_df, key=f"total_{scenario}", num_rows="fixed", use_container_width=True)
    st.session_state.total_df = total_df
with right:
    st.markdown("**Allocation matrix**")
    alloc_df = st.data_editor(st.session_state.alloc_df, key=f"alloc_{scenario}", num_rows="fixed", use_container_width=True)
    st.session_state.alloc_df = alloc_df

left, right = st.columns([1, 1])
with left:
    st.markdown("**Maximum demand matrix**")
    max_df = st.data_editor(st.session_state.max_df, key=f"max_{scenario}", num_rows="fixed", use_container_width=True)
    st.session_state.max_df = max_df
with right:
    st.markdown("**Current outstanding requests**")
    req_df = st.data_editor(st.session_state.req_df, key=f"req_{scenario}", num_rows="fixed", use_container_width=True)
    st.session_state.req_df = req_df

errors = []
try:
    total = [int(total_df.iloc[0][r]) for r in resources]
    allocation = [[int(alloc_df.loc[p, r]) for r in resources] for p in processes]
    max_demand = [[int(max_df.loc[p, r]) for r in resources] for p in processes]
    requests = [[int(req_df.loc[p, r]) for r in resources] for p in processes]
    if any(x < 0 for x in total):
        errors.append("Total resource counts cannot be negative.")
    if any(x < 0 for row in allocation + max_demand + requests for x in row):
        errors.append("Allocation, maximum demand and requests must be non-negative.")
    for j, r in enumerate(resources):
        allocated_sum = sum(allocation[i][j] for i in range(len(processes)))
        if allocated_sum > total[j]:
            errors.append(f"{r}: allocations ({allocated_sum}) exceed total instances ({total[j]}).")
    for i, p in enumerate(processes):
        for j, r in enumerate(resources):
            if max_demand[i][j] < allocation[i][j]:
                errors.append(f"{p}: maximum demand for {r} is below its current allocation.")
except Exception:
    errors.append("Enter whole-number values in all matrix cells.")

if errors:
    for e in errors:
        st.error(e)
    st.stop()

available = [total[j] - sum(allocation[i][j] for i in range(len(processes))) for j in range(len(resources))]
need = [[max_demand[i][j] - allocation[i][j] for j in range(len(resources))] for i in range(len(processes))]
data = {
    "case": scenario, "processes": processes, "resources": resources, "total": total,
    "allocation": allocation, "max_demand": max_demand, "requests": requests, "available": available,
}

st.markdown("---")
st.subheader("02 / Investigation")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Processes", len(processes))
m2.metric("Resource types", len(resources))
m3.metric("Available vector", str(available))
safe, sequence, need, trace, blocked = bankers(processes, allocation, max_demand, available)
m4.metric("Banker's result", "SAFE" if safe else "UNSAFE")

with st.expander("View calculated Need matrix", expanded=True):
    st.dataframe(pd.DataFrame(need, columns=resources, index=processes), use_container_width=True)

tab_graph, tab_bankers, tab_dfs, tab_verdict = st.tabs(["Resource graph", "Banker's Algorithm", "DFS cycle analysis", "Verdict & recovery"])

graph = build_rag(processes, resources, allocation, requests)
cycles = find_cycles(graph)

with tab_graph:
    st.markdown("**Resource Allocation Graph (RAG)**")
    st.caption("Assignment edges point from resource to process; request edges point from process to resource.")
    st.pyplot(draw_graph(graph, blocked), use_container_width=True)
    if graph.number_of_edges() == 0:
        st.info("No allocation or request edges are present. Edit the matrices to add edges.")

with tab_bankers:
    st.markdown("**Safe-state analysis trace**")
    st.write("Need = Maximum Demand − Allocation")
    st.write("Work begins as Available. A process can finish when its remaining Need is no greater than Work.")
    for i, line in enumerate(trace, start=1):
        st.code(f"{i:02d}  {line}", language="text")
    if safe:
        st.success("SAFE STATE — one valid safe sequence is: " + " → ".join(sequence))
    else:
        st.warning("UNSAFE STATE — no complete safe sequence was found for this snapshot. This does not, by itself, prove that the system is currently deadlocked.")
        st.write("Unfinished processes:", ", ".join(blocked) if blocked else "None")

with tab_dfs:
    st.markdown("**Directed cycle analysis**")
    st.caption("DFS is used here to inspect directed cycles in the graph. With multiple resource instances, a cycle alone is not conclusive proof of deadlock.")
    if cycles:
        for i, cycle in enumerate(cycles, start=1):
            st.write(f"Cycle {i}: " + " → ".join(cycle + [cycle[0]]))
        if safe:
            st.info("A graph cycle exists, but Banker's Algorithm found a safe sequence for the current allocation snapshot.")
        else:
            st.warning("A graph cycle and an unsafe snapshot were both found. Review the resource instances and outstanding requests before concluding that deadlock is proven.")
    else:
        st.success("No directed cycle found in the current Resource Allocation Graph.")
    st.markdown("**Current request edges**")
    request_rows = []
    for i, p in enumerate(processes):
        for j, r in enumerate(resources):
            if requests[i][j] > 0:
                request_rows.append({"Process": p, "Requests resource": r, "Instances requested": requests[i][j]})
    if request_rows:
        st.dataframe(pd.DataFrame(request_rows), use_container_width=True)
    else:
        st.caption("No outstanding requests are entered.")

with tab_verdict:
    st.markdown("**Investigation verdict**")
    if safe:
        st.success("SAFE SNAPSHOT — all processes can finish in the computed order.")
        st.metric("Safe sequence", " → ".join(sequence))
    else:
        st.error("UNSAFE SNAPSHOT — at least one process cannot be placed in a complete safe sequence.")
        st.write("Unfinished processes:", ", ".join(blocked))
    if cycles:
        st.warning(f"Graph cycle(s) found: {len(cycles)}. A cycle is not automatically a deadlock proof for multi-instance resources.")
    else:
        st.info("No graph cycle was found.")
    st.markdown("#### Recovery options to evaluate")
    for title, action, cost in recovery_suggestions(blocked, resources, allocation, requests, processes):
        with st.expander(f"{title} · Cost: {cost}"):
            st.write(action)
    st.caption("Recovery suggestions are educational options, not automatic actions on a real operating system.")

report = make_report(data)
st.markdown("---")
st.subheader("03 / Export case report")
st.caption("Download the inputs, computed matrices, safe-state result, cycle analysis and recovery suggestions.")
json_bytes = json.dumps(report, indent=2).encode("utf-8")
st.download_button("⬇ Download JSON report", data=json_bytes, file_name="deadlock_investigation_report.json", mime="application/json")
txt = [
    "DEADLOCK DETECTIVE — INVESTIGATION REPORT",
    f"Generated: {report['generated_at']}",
    f"Case: {scenario}",
    f"Processes: {processes}",
    f"Resources: {resources}",
    f"Total: {total}",
    f"Available: {available}",
    f"Allocation: {allocation}",
    f"Maximum demand: {max_demand}",
    f"Need: {need}",
    f"Banker's result: {'SAFE' if safe else 'UNSAFE'}",
    f"Safe sequence: {' -> '.join(sequence) if safe else 'None found'}",
    f"Unfinished processes: {blocked}",
    "Banker's trace:",
    *trace,
    "Graph cycles:",
    *[(" -> ".join(c + [c[0]])) for c in cycles],
    report["cycle_note"],
    "Recovery suggestions:",
    *[f"- {name} (cost: {cost}): {description}" for name, description, cost in report["recovery_suggestions"]],
]
st.download_button("⬇ Download text report", data="\n".join(txt), file_name="deadlock_investigation_report.txt", mime="text/plain")

with st.expander("About this project"):
    st.write("Deadlock Detective is an educational Operating Systems simulator inspired by the supplied project report. It models a snapshot of resource allocation; it does not monitor live OS processes.")
    st.write("Technologies: Python, Streamlit, NetworkX, Matplotlib and Pandas.")
