import os
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from config import DEFAULT_CONFIG
from simulation.engine import run_simulation


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Energy-Aware VM Consolidation",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------
# CUSTOM DARK DASHBOARD THEME
# --------------------------------------------------

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background:
            radial-gradient(circle at 12% 0%, rgba(32, 87, 150, 0.16), transparent 28%),
            #0b1120;
        color: #e5e7eb;
    }

    [data-testid="stSidebar"] {
        background: #0d1728;
        border-right: 1px solid rgba(148, 163, 184, 0.13);
    }

    [data-testid="stSidebar"] * {
        color: #dbeafe;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1500px;
    }

    h1, h2, h3 {
        color: #f8fafc !important;
        letter-spacing: -0.035em;
    }

    [data-testid="stMetric"] {
        background: linear-gradient(145deg, #152238, #111c2e);
        border: 1px solid rgba(148, 163, 184, 0.16);
        border-radius: 15px;
        padding: 18px 20px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.14);
    }

    [data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
        font-size: 0.84rem;
    }

    [data-testid="stMetricValue"] {
        color: #f8fafc !important;
        font-weight: 750;
    }

    div[data-testid="stTabs"] button {
        color: #94a3b8;
        font-weight: 600;
    }

    div[data-testid="stTabs"] button[aria-selected="true"] {
        color: #60a5fa;
    }

    .hero {
        background: linear-gradient(115deg, #142b49 0%, #142039 55%, #172033 100%);
        border: 1px solid rgba(96, 165, 250, 0.22);
        border-radius: 20px;
        padding: 25px 28px;
        margin-bottom: 24px;
    }

    .hero-kicker {
        color: #7dd3fc;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-bottom: 8px;
    }

    .hero-title {
        color: #f8fafc;
        font-size: 2rem;
        line-height: 1.2;
        font-weight: 800;
        margin-bottom: 8px;
    }

    .hero-subtitle {
        color: #b6c7dc;
        font-size: 0.96rem;
        margin: 0;
    }

    .section-note {
        color: #94a3b8;
        font-size: 0.88rem;
        margin-top: -8px;
        margin-bottom: 18px;
    }

    .status-card {
        background: #121f33;
        border: 1px solid rgba(148, 163, 184, 0.15);
        border-radius: 13px;
        padding: 15px 17px;
        margin-bottom: 10px;
    }

    .status-name {
        color: #e2e8f0;
        font-weight: 700;
        font-size: 0.95rem;
    }

    .status-detail {
        color: #94a3b8;
        font-size: 0.82rem;
        margin-top: 5px;
    }

    .small-label {
        color: #94a3b8;
        font-size: 0.76rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 700;
    }

    .sidebar-caption {
        color: #8295ad;
        font-size: 0.78rem;
        line-height: 1.5;
    }

    div.stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #2563eb, #0ea5e9);
        border: 0;
        border-radius: 10px;
        font-weight: 700;
        min-height: 44px;
    }

    div.stDownloadButton > button {
        border-radius: 9px;
        border: 1px solid rgba(96, 165, 250, 0.35);
        background: #14243b;
        color: #dbeafe;
    }

    [data-testid="stDataFrame"] {
        border: 1px solid rgba(148, 163, 184, 0.14);
        border-radius: 12px;
        overflow: hidden;
    }

    hr {
        border-color: rgba(148, 163, 184, 0.16);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

CHART_TEMPLATE = "plotly_dark"
CHART_LAYOUT = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "font": {"color": "#cbd5e1", "family": "Inter"},
    "margin": {"l": 20, "r": 20, "t": 55, "b": 20},
    "legend": {"orientation": "h", "y": 1.12},
}


def style_chart(fig, height=360):
    fig.update_layout(template=CHART_TEMPLATE, height=height, **CHART_LAYOUT)
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="rgba(148,163,184,0.12)", zeroline=False)
    return fig


def show_empty(message):
    st.info(message)


# --------------------------------------------------
# SIDEBAR: SIMULATION SETTINGS + NAVIGATION
# --------------------------------------------------

with st.sidebar:
    st.markdown("## ⚡ Data Centre")
    st.markdown(
        '<div class="sidebar-caption">ENERGY-AWARE VM CONSOLIDATION<br>'
        "Simulation control panel</div>",
        unsafe_allow_html=True,
    )
    st.divider()

    st.markdown("### Simulation settings")

    num_hosts = st.slider(
        "Physical hosts", 3, 20, int(DEFAULT_CONFIG["num_hosts"])
    )
    num_vms = st.slider(
        "Virtual machines", 5, 80, int(DEFAULT_CONFIG["num_vms"])
    )
    host_capacity = st.number_input(
        "CPU capacity per host",
        min_value=50.0,
        max_value=500.0,
        value=float(DEFAULT_CONFIG["host_capacity"]),
        step=10.0,
    )
    steps = st.slider(
        "Simulation time steps",
        12,
        144,
        int(DEFAULT_CONFIG["simulation_steps"]),
        step=4,
    )
    step_minutes = st.selectbox(
        "Minutes per step", [5, 10, 15, 30, 60], index=2
    )
    underload_pct = st.slider(
        "Underload threshold (%)",
        10,
        60,
        int(DEFAULT_CONFIG["underload_threshold"] * 100),
    )
    safety_pct = st.slider(
        "Safe maximum utilization (%)",
        70,
        100,
        int(DEFAULT_CONFIG["safety_threshold"] * 100),
    )
    idle_power = st.number_input(
        "Idle power (W)",
        min_value=50.0,
        max_value=300.0,
        value=float(DEFAULT_CONFIG["idle_power_w"]),
        step=5.0,
    )
    max_power = st.number_input(
        "Maximum power (W)",
        min_value=100.0,
        max_value=500.0,
        value=float(DEFAULT_CONFIG["max_power_w"]),
        step=5.0,
    )
    migration_cost = st.number_input(
        "Migration energy cost (Wh)",
        min_value=0.0,
        max_value=100.0,
        value=float(DEFAULT_CONFIG["migration_energy_wh"]),
        step=1.0,
    )
    vm_selection = st.selectbox(
        "VM selection strategy",
        [
            "Minimum CPU first",
            "Maximum CPU first",
            "Minimum migration time",
        ],
    )
    seed = st.number_input(
        "Random seed", 0, 100000, int(DEFAULT_CONFIG["seed"])
    )

    config = {
        "num_hosts": num_hosts,
        "num_vms": num_vms,
        "host_capacity": float(host_capacity),
        "simulation_steps": steps,
        "step_minutes": step_minutes,
        "underload_threshold": underload_pct / 100.0,
        "overload_threshold": DEFAULT_CONFIG["overload_threshold"],
        "safety_threshold": safety_pct / 100.0,
        "idle_power_w": float(idle_power),
        "max_power_w": float(max(max_power, idle_power)),
        "migration_energy_wh": float(migration_cost),
        "migration_overhead": DEFAULT_CONFIG["migration_overhead"],
        "seed": int(seed),
    }

    if num_vms < num_hosts:
        st.warning(
            "For meaningful consolidation, use at least as many VMs "
            "as physical hosts."
        )

    run_button = st.button(
        "▶  Run simulation", type="primary", use_container_width=True
    )

    st.divider()
    st.markdown("### Workspace")
    page = st.radio(
        "Navigate",
        [
            "Overview",
            "Energy Analytics",
            "Host Monitoring",
            "VM Migrations",
            "SLA Monitoring",
            "Break-even Analysis",
            "Data & Export",
        ],
        label_visibility="collapsed",
    )
    st.markdown(
        '<div class="sidebar-caption">Configure your environment, run a '
        "simulation, and explore the results from the sections above.</div>",
        unsafe_allow_html=True,
    )


# --------------------------------------------------
# RUN SIMULATION AND STORE RESULTS
# --------------------------------------------------

if run_button:
    if num_vms < 1 or num_hosts < 1:
        st.error("Configure at least one host and one VM.")
        st.stop()

    with st.spinner("Simulating data centre operations..."):
        results = run_simulation(config, vm_selection)

    st.session_state["results"] = results
    st.session_state["config"] = config
    st.session_state["vm_selection"] = vm_selection

if "results" not in st.session_state:
    st.markdown(
        """
        <div class="hero">
            <div class="hero-kicker">Cloud infrastructure simulator</div>
            <div class="hero-title">Energy-Aware VM Consolidation</div>
            <p class="hero-subtitle">
                Monitor server utilization, compare consolidation policies,
                evaluate migration costs, and understand energy performance.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.info(
        "Set your data centre parameters in the sidebar, then click "
        "**Run simulation** to generate dashboard results."
    )

    st.markdown("### Platform capabilities")
    feature_cols = st.columns(3)
    features = [
        ("🖥️", "Host & VM simulation", "Model physical hosts and virtual machines."),
        ("📈", "Dynamic workloads", "Generate changing CPU demand over time."),
        ("🔁", "VM consolidation", "Move VMs and switch off empty hosts."),
        ("⚡", "Energy analysis", "Compare operational and migration energy."),
        ("🛡️", "SLA monitoring", "Track safety and CPU capacity violations."),
        ("⚖️", "Break-even decisions", "Check whether migration is worth its energy cost."),
    ]
    for col, (emoji, title, description) in zip(feature_cols * 2, features):
        with col:
            st.markdown(
                f"""
                <div class="status-card">
                    <div style="font-size:1.4rem">{emoji}</div>
                    <div class="status-name">{title}</div>
                    <div class="status-detail">{description}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.stop()


# --------------------------------------------------
# PREPARE RESULTS (SAME METRICS AS THE ORIGINAL UI)
# --------------------------------------------------

results = st.session_state["results"]
saved_config = st.session_state["config"]
safety_limit = saved_config["safety_threshold"] * 100
simulation_steps = saved_config["simulation_steps"]

summary = []
host_data = {}
migration_data = {}
baseline = results["No Consolidation"].total_energy_wh

for name, result in results.items():
    host_df = pd.DataFrame(result.host_rows)
    migration_df = pd.DataFrame(result.migration_rows)

    host_data[name] = host_df
    migration_data[name] = migration_df

    capacity_violations = int(
        (
            (host_df["active"] == True)
            & (host_df["utilization_pct"] > 100)
        ).sum()
    )
    safety_violations = result.sla_violations
    energy_savings = (
        (baseline - result.total_energy_wh) / baseline * 100
        if baseline > 0
        else 0
    )
    max_utilization = (
        host_df.loc[host_df["active"], "utilization_pct"].max()
        if host_df["active"].any()
        else 0
    )
    final_active_hosts = int(
        host_df[host_df["step"] == simulation_steps]["active"].sum()
    )

    summary.append(
        {
            "Policy": name,
            "Total energy (Wh)": round(result.total_energy_wh, 2),
            "Energy saved (%)": round(energy_savings, 2),
            "Operational energy (Wh)": round(result.operational_energy_wh, 2),
            "Migration energy (Wh)": round(result.migration_energy_wh, 2),
            "Migrations": result.migrations,
            "Hosts switched off": result.hosts_shutdown,
            "Active hosts at end": final_active_hosts,
            "Safety violations (> threshold)": safety_violations,
            "Capacity violations (>100%)": capacity_violations,
            "Maximum CPU utilization (%)": round(max_utilization, 2),
        }
    )

summary_df = pd.DataFrame(summary)

best_policy = min(results.values(), key=lambda r: r.total_energy_wh)
best_energy = best_policy.total_energy_wh
best_savings = (
    (baseline - best_energy) / baseline * 100 if baseline > 0 else 0
)
best_name = best_policy.name
total_migrations = sum(result.migrations for result in results.values())
total_shutdowns = sum(result.hosts_shutdown for result in results.values())


# --------------------------------------------------
# COMMON HEADER
# --------------------------------------------------

st.markdown(
    f"""
    <div class="hero">
        <div class="hero-kicker">Live simulation workspace</div>
        <div class="hero-title">⚡ Energy-Aware VM Consolidation</div>
        <p class="hero-subtitle">
            Comparing {len(results)} consolidation policies across
            {saved_config['num_hosts']} physical hosts and
            {saved_config['num_vms']} virtual machines.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# OVERVIEW PAGE
# --------------------------------------------------

if page == "Overview":
    st.subheader("Simulation Overview")
    st.markdown(
        '<div class="section-note">A high-level view of energy efficiency '
        "and consolidation performance.</div>",
        unsafe_allow_html=True,
    )

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Baseline energy", f"{baseline:,.2f} Wh")
    k2.metric("Best policy energy", f"{best_energy:,.2f} Wh")
    k3.metric("Energy reduction", f"{best_savings:.2f}%")
    k4.metric("Best-performing policy", best_name)

    st.markdown("### Policy performance")
    left, right = st.columns([1.25, 1])
    with left:
        fig = px.bar(
            summary_df,
            x="Policy",
            y="Total energy (Wh)",
            color="Policy",
            text="Total energy (Wh)",
            title="Total energy consumption",
        )
        fig.update_traces(texttemplate="%{text:.1f} Wh", textposition="outside")
        st.plotly_chart(style_chart(fig, 390), use_container_width=True)
    with right:
        fig = px.bar(
            summary_df,
            x="Policy",
            y="Energy saved (%)",
            color="Policy",
            text="Energy saved (%)",
            title="Energy reduction vs baseline",
        )
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        st.plotly_chart(style_chart(fig, 390), use_container_width=True)

    st.markdown("### Consolidation comparison")
    st.dataframe(summary_df, use_container_width=True, hide_index=True)
    st.caption(
        "Safety violations count active-host intervals above the configured "
        "safety threshold. Capacity violations count active-host intervals "
        "exceeding 100% CPU capacity."
    )

    st.markdown("### Run configuration")
    cfg1, cfg2, cfg3, cfg4 = st.columns(4)
    cfg1.metric("Physical hosts", saved_config["num_hosts"])
    cfg2.metric("Virtual machines", saved_config["num_vms"])
    cfg3.metric("Simulation steps", saved_config["simulation_steps"])
    cfg4.metric("Step duration", f"{saved_config['step_minutes']} min")


# --------------------------------------------------
# ENERGY ANALYTICS PAGE
# --------------------------------------------------

elif page == "Energy Analytics":
    st.subheader("Energy Analytics")
    st.markdown(
        '<div class="section-note">Understand where energy is consumed '
        "and how consolidation changes the total.</div>",
        unsafe_allow_html=True,
    )

    e1, e2, e3 = st.columns(3)
    e1.metric("Baseline energy", f"{baseline:,.2f} Wh")
    e2.metric("Best policy energy", f"{best_energy:,.2f} Wh")
    e3.metric("Estimated reduction", f"{best_savings:.2f}%")

    fig1 = px.bar(
        summary_df,
        x="Policy",
        y="Total energy (Wh)",
        color="Policy",
        text="Total energy (Wh)",
        title="Total energy including migration cost",
    )
    fig1.update_traces(textposition="outside")
    st.plotly_chart(style_chart(fig1, 390), use_container_width=True)

    energy_df = pd.concat(
        [
            pd.DataFrame(result.step_rows).assign(Policy=name)
            for name, result in results.items()
        ],
        ignore_index=True,
    )
    if not energy_df.empty:
        fig2 = px.line(
            energy_df,
            x="time_minutes",
            y="operational_energy_wh",
            color="Policy",
            markers=True,
            title="Operational energy per simulation interval",
        )
        fig2.update_layout(
            xaxis_title="Simulation time (minutes)",
            yaxis_title="Energy per interval (Wh)",
        )
        st.plotly_chart(style_chart(fig2, 390), use_container_width=True)

    fig3 = px.bar(
        summary_df,
        x="Policy",
        y=["Operational energy (Wh)", "Migration energy (Wh)"],
        barmode="group",
        title="Operational energy vs migration energy",
    )
    st.plotly_chart(style_chart(fig3, 390), use_container_width=True)

    st.success(
        f"{best_name} achieved the lowest estimated total energy "
        f"consumption: {best_energy:,.2f} Wh."
    )
    st.caption(
        "Energy values are model-based estimates from the simulator, "
        "not physical electricity meter readings."
    )


# --------------------------------------------------
# HOST MONITORING PAGE
# --------------------------------------------------

elif page == "Host Monitoring":
    st.subheader("Physical Host Monitoring")
    st.markdown(
        '<div class="section-note">Inspect host activity, CPU utilization, '
        "and power consumption at any simulation step.</div>",
        unsafe_allow_html=True,
    )

    selected_policy = st.selectbox(
        "Consolidation policy", list(results.keys()), key="host_policy"
    )
    host_df = host_data[selected_policy].copy()

    selected_step = st.slider(
        "Simulation time step",
        1,
        simulation_steps,
        simulation_steps,
        key="host_step",
    )
    snapshot = host_df[host_df["step"] == selected_step].copy()

    def get_host_status(row):
        if not row["active"]:
            return "Powered Off"
        if row["utilization_pct"] > 100:
            return "Overloaded"
        if row["utilization_pct"] > safety_limit:
            return "Above Safety Limit"
        return "Active"

    snapshot["Status"] = snapshot.apply(get_host_status, axis=1)

    active_count = int(snapshot["active"].sum())
    inactive_count = len(snapshot) - active_count
    highest_utilization = (
        snapshot["utilization_pct"].max() if not snapshot.empty else 0
    )
    h1, h2, h3 = st.columns(3)
    h1.metric("Active hosts", active_count)
    h2.metric("Powered-off hosts", inactive_count)
    h3.metric("Highest CPU utilization", f"{highest_utilization:.2f}%")

    fig = px.bar(
        snapshot,
        x="host_id",
        y="utilization_pct",
        color="Status",
        text="utilization_pct",
        hover_data=["cpu_demand", "vm_count", "power_w"],
        color_discrete_map={
            "Active": "#22c55e",
            "Powered Off": "#64748b",
            "Above Safety Limit": "#f59e0b",
            "Overloaded": "#ef4444",
        },
        title=f"Host CPU utilization — step {selected_step}",
    )
    fig.add_hline(
        y=safety_limit,
        line_dash="dash",
        line_color="#f59e0b",
        annotation_text="Safety threshold",
    )
    fig.add_hline(
        y=100,
        line_dash="dot",
        line_color="#ef4444",
        annotation_text="Maximum CPU capacity",
    )
    fig.update_layout(
        xaxis_title="Physical host", yaxis_title="CPU utilization (%)"
    )
    st.plotly_chart(style_chart(fig, 420), use_container_width=True)

    st.markdown("### Host status cards")
    cards = st.columns(4)
    for index, (_, row) in enumerate(snapshot.iterrows()):
        status = row["Status"]
        status_color = {
            "Active": "#22c55e",
            "Powered Off": "#94a3b8",
            "Above Safety Limit": "#f59e0b",
            "Overloaded": "#ef4444",
        }.get(status, "#94a3b8")
        with cards[index % 4]:
            st.markdown(
                f"""
                <div class="status-card">
                    <div class="status-name">{row['host_id']}</div>
                    <div style="color:{status_color};font-size:0.8rem;
                                font-weight:700;margin-top:5px">{status}</div>
                    <div class="status-detail">
                        CPU: {row['utilization_pct']:.1f}%<br>
                        VMs: {int(row['vm_count'])}<br>
                        Power: {row['power_w']:.1f} W
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("### Host performance records")
    st.dataframe(snapshot, use_container_width=True, hide_index=True)


# --------------------------------------------------
# VM MIGRATIONS PAGE
# --------------------------------------------------

elif page == "VM Migrations":
    st.subheader("VM Migration Activity")
    st.markdown(
        '<div class="section-note">Review VM movement, migration energy, '
        "and host shutdowns for each policy.</div>",
        unsafe_allow_html=True,
    )

    migration_policy = st.selectbox(
        "Consolidation policy", list(results.keys()), key="migration_policy"
    )
    migration_df = migration_data[migration_policy]
    migration_result = results[migration_policy]

    m1, m2, m3 = st.columns(3)
    m1.metric("Total migrations", migration_result.migrations)
    m2.metric("Migration energy", f"{migration_result.migration_energy_wh:.2f} Wh")
    m3.metric("Hosts switched off", migration_result.hosts_shutdown)

    if migration_df.empty:
        show_empty("No VM migrations were performed under this policy.")
    else:
        st.markdown("### Migration history")
        st.dataframe(
            migration_df, use_container_width=True, hide_index=True
        )

        migration_counts = (
            migration_df.groupby("step")
            .size()
            .reset_index(name="migrations")
        )
        fig = px.bar(
            migration_counts,
            x="step",
            y="migrations",
            text="migrations",
            title="VM migrations per simulation step",
        )
        fig.update_layout(
            xaxis_title="Simulation step", yaxis_title="Number of migrations"
        )
        st.plotly_chart(style_chart(fig, 360), use_container_width=True)


# --------------------------------------------------
# SLA MONITORING PAGE
# --------------------------------------------------

elif page == "SLA Monitoring":
    st.subheader("SLA & Capacity Monitoring")
    st.markdown(
        f'<div class="section-note">Configured safe CPU utilization '
        f"threshold: <b>{safety_limit:.0f}%</b>. Safety and physical "
        "capacity violations are tracked separately.</div>",
        unsafe_allow_html=True,
    )

    sla_policy = st.selectbox(
        "Consolidation policy", list(results.keys()), key="sla_policy"
    )
    sla_result = results[sla_policy]
    sla_hosts = host_data[sla_policy]

    safety_violations = sla_result.sla_violations
    capacity_violations = int(
        (
            (sla_hosts["active"] == True)
            & (sla_hosts["utilization_pct"] > 100)
        ).sum()
    )
    total_host_intervals = len(sla_hosts) or 1
    violation_rate = safety_violations / total_host_intervals * 100

    s1, s2, s3 = st.columns(3)
    s1.metric("Safety threshold violations", safety_violations)
    s2.metric("Actual capacity violations", capacity_violations)
    s3.metric("Safety violation rate", f"{violation_rate:.2f}%")

    violations_df = sla_hosts[
        (sla_hosts["active"] == True)
        & (sla_hosts["utilization_pct"] > safety_limit)
    ].copy()
    overload_df = sla_hosts[
        (sla_hosts["active"] == True)
        & (sla_hosts["utilization_pct"] > 100)
    ].copy()

    st.markdown("### Safety threshold")
    if violations_df.empty:
        st.success(
            "No active host exceeded the configured safety threshold "
            "during this simulation."
        )
    else:
        st.warning("Some hosts exceeded the configured safety threshold.")
        st.dataframe(
            violations_df, use_container_width=True, hide_index=True
        )

    st.markdown("### Physical CPU capacity")
    if overload_df.empty:
        st.success("No physical host exceeded 100% CPU capacity.")
    else:
        st.error(
            f"{len(overload_df)} host-time capacity violations detected."
        )
        st.dataframe(overload_df, use_container_width=True, hide_index=True)


# --------------------------------------------------
# BREAK-EVEN ANALYSIS PAGE
# --------------------------------------------------

elif page == "Break-even Analysis":
    st.subheader("VM Migration Break-even Analysis")
    st.markdown(
        """
        <div class="section-note">
        This analysis checks whether the expected operational energy savings
        from consolidating an underloaded host are greater than the energy
        cost of migration, while keeping future placement within the
        configured CPU safety limit.
        </div>
        """,
        unsafe_allow_html=True,
    )

    break_even_policy = st.selectbox(
        "Consolidation policy", list(results.keys()), key="break_even_policy"
    )
    be_result = results[break_even_policy]
    be_rows = getattr(be_result, "break_even_rows", [])
    skipped = getattr(be_result, "migrations_skipped_not_worthwhile", 0)

    if break_even_policy == "No Consolidation":
        show_empty(
            "No Consolidation does not perform VM consolidation. "
            "Therefore, break-even analysis is not applicable."
        )
    elif not be_rows:
        show_empty(
            "No underloaded hosts were considered for consolidation "
            "in this simulation."
        )
    else:
        be_df = pd.DataFrame(be_rows)
        approved_df = be_df[be_df["worthwhile"] == True]
        rejected_df = be_df[be_df["worthwhile"] == False]

        total_expected_savings = be_df[
            "expected_operational_savings_wh"
        ].sum()
        total_migration_cost = be_df["migration_cost_wh"].sum()
        total_net_savings = be_df["net_energy_savings_wh"].sum()

        b1, b2, b3, b4 = st.columns(4)
        b1.metric("Evaluations", len(be_df))
        b2.metric("Approved decisions", len(approved_df))
        b3.metric("Rejected decisions", len(rejected_df))
        b4.metric("Skipped decisions", skipped)

        st.markdown("### Energy break-even summary")
        c1, c2, c3 = st.columns(3)
        c1.metric(
            "Expected operational savings",
            f"{total_expected_savings:,.2f} Wh",
        )
        c2.metric("Migration energy cost", f"{total_migration_cost:,.2f} Wh")
        c3.metric("Net expected savings", f"{total_net_savings:,.2f} Wh")

        st.caption(
            "These totals represent consolidation evaluations. Multiple "
            "evaluations can overlap in their forecast horizons, so they "
            "must not be interpreted as additive realized energy savings."
        )

        st.markdown("### Consolidation decision history")
        display_columns = [
            "step",
            "source_host",
            "vms_to_migrate",
            "expected_operational_savings_wh",
            "migration_cost_wh",
            "net_energy_savings_wh",
            "estimated_payback_steps",
            "future_placement_safe",
            "worthwhile",
            "decision",
        ]
        available_columns = [
            column for column in display_columns if column in be_df.columns
        ]
        st.dataframe(
            be_df[available_columns],
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("### Expected savings vs migration cost")
        chart_df = be_df.melt(
            id_vars=["step", "source_host"],
            value_vars=[
                "expected_operational_savings_wh",
                "migration_cost_wh",
            ],
            var_name="Energy metric",
            value_name="Energy (Wh)",
        )
        fig = px.bar(
            chart_df,
            x="source_host",
            y="Energy (Wh)",
            color="Energy metric",
            barmode="group",
            hover_data=["step"],
            title="Expected operational savings vs migration cost",
        )
        st.plotly_chart(style_chart(fig, 390), use_container_width=True)

        st.markdown("### Decision explanations")
        for _, row in be_df.iterrows():
            decision_label = (
                "Approved" if row["worthwhile"] else "Rejected"
            )
            with st.expander(
                f"Step {row['step']} | {row['source_host']} | {decision_label}"
            ):
                st.write(f"**VMs to migrate:** {row['vms_to_migrate']}")
                st.write(
                    "**Expected operational savings:** "
                    f"{row['expected_operational_savings_wh']} Wh"
                )
                st.write(
                    f"**Migration cost:** {row['migration_cost_wh']} Wh"
                )
                st.write(
                    f"**Net expected savings:** "
                    f"{row['net_energy_savings_wh']} Wh"
                )
                st.write(
                    f"**Estimated payback:** "
                    f"{row['estimated_payback_steps']} steps"
                )
                st.write(
                    f"**Future placement safe:** "
                    f"{row['future_placement_safe']}"
                )
                st.write(f"**Decision:** {row['decision']}")

        st.download_button(
            "⬇ Download break-even analysis CSV",
            be_df.to_csv(index=False).encode("utf-8"),
            file_name="break_even_analysis.csv",
            mime="text/csv",
        )


# --------------------------------------------------
# DATA & EXPORT PAGE
# --------------------------------------------------

elif page == "Data & Export":
    st.subheader("Simulation Data & Export")
    st.markdown(
        '<div class="section-note">Inspect detailed simulation records '
        "and download CSV files for your report.</div>",
        unsafe_allow_html=True,
    )

    detail_policy = st.selectbox(
        "Consolidation policy", list(results.keys()), key="detail_policy"
    )
    detail_result = results[detail_policy]
    detail_df = pd.DataFrame(detail_result.step_rows)
    host_export = host_data[detail_policy]
    migration_export = migration_data[detail_policy]

    st.markdown("### Time-step simulation records")
    st.dataframe(detail_df, use_container_width=True, hide_index=True)
    st.download_button(
        "⬇ Download time-step results CSV",
        detail_df.to_csv(index=False).encode("utf-8"),
        file_name="time_step_results.csv",
        mime="text/csv",
    )

    st.markdown("### Host performance records")
    st.dataframe(host_export, use_container_width=True, hide_index=True)
    st.download_button(
        "⬇ Download host metrics CSV",
        host_export.to_csv(index=False).encode("utf-8"),
        file_name="host_metrics.csv",
        mime="text/csv",
    )

    st.markdown("### Migration records")
    if migration_export.empty:
        show_empty("There are no migration records for this policy.")
    else:
        st.dataframe(
            migration_export, use_container_width=True, hide_index=True
        )
    st.download_button(
        "⬇ Download migration history CSV",
        migration_export.to_csv(index=False).encode("utf-8"),
        file_name="migration_history.csv",
        mime="text/csv",
    )

    st.markdown("### Policy comparison")
    st.dataframe(summary_df, use_container_width=True, hide_index=True)
    st.download_button(
        "⬇ Download policy comparison CSV",
        summary_df.to_csv(index=False).encode("utf-8"),
        file_name="policy_comparison.csv",
        mime="text/csv",
    )


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()
st.caption(
    "Energy-Aware VM Consolidation | Mathematical data-centre simulation. "
    "Energy and migration values are model-based estimates, not physical "
    "electricity meter measurements."
)
