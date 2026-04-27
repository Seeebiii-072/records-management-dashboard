"""
app.py - Records Management AI Dashboard
=========================================
Auto-installs Ollama + llama3 on first run.
Pure Streamlit — no HTML/CSS.
"""

import streamlit as st
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import io, sys, os

sys.path.insert(0, os.path.dirname(__file__))

from scripts.pdf_reader    import read_pdf
from scripts.ai_extractor  import hybrid_extract
from scripts.processor     import to_dataframe, get_summary_stats
from scripts.utils         import build_graph
from scripts.ollama_setup  import (
    setup_ollama, is_ollama_installed,
    is_ollama_running, is_model_available,
    OLLAMA_MODEL
)

# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Records Management AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

COLORS = {
    "System Owner":      "#00D4FF",
    "Workflow User":     "#FF6B35",
    "Records Officer":   "#7C3AED",
    "Records Custodian": "#10B981",
}
installed = is_ollama_installed()
running = is_ollama_running()
model_ok = is_model_available() if running else False
# ── HEADER ────────────────────────────────────────────────────────────────────
st.title("🧠 Records Management Intelligence Dashboard")
st.caption("PDF → Ollama LLM (auto-installed) → Department & Tool Mapping → Dashboard")
st.divider()

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
# with st.sidebar:
#     st.header("🤖 Ollama LLM Status")

#     installed = is_ollama_installed()
#     running   = is_ollama_running()
#     model_ok  = is_model_available() if running else False

#     st.markdown(f"**Installed:** {'✅ Yes' if installed else '❌ No'}")
#     st.markdown(f"**Server:**    {'✅ Running' if running else '🔴 Stopped'}")
#     st.markdown(f"**Model:**     {'✅ ' + OLLAMA_MODEL if model_ok else '❌ Not pulled'}")

#     st.divider()

#     if not (installed and running and model_ok):
#         st.warning("Ollama not ready. Click below to auto-setup.")
#         if st.button("⚡ Auto-Setup Ollama", use_container_width=True, type="primary"):
#             with st.status("Setting up Ollama...", expanded=True) as status:
#                 log = st.empty()
#                 messages = []

#                 def cb(msg):
#                     messages.append(msg)
#                     log.markdown("\n\n".join(messages[-6:]))

#                 ok, msg = setup_ollama(status_callback=cb)

#                 if ok:
#                     status.update(label="✅ Ollama Ready!", state="complete")
#                     st.success(msg)
#                     st.rerun()
#                 else:
#                     status.update(label="❌ Setup Failed", state="error")
#                     st.error(msg)
#                     st.markdown("""
# **Manual Install:**
# 1. Go to https://ollama.com
# 2. Download & install
# 3. Run: `ollama pull llama3`
# 4. Restart this app
#                     """)
#     else:
#         st.success(f"✅ Ollama + {OLLAMA_MODEL} ready!")

#     st.divider()
#     st.subheader("🔗 Relationship Types")
#     st.markdown("🔵 **System Owner** — IT owns the system")
#     st.markdown("🟠 **Workflow User** — Daily operational use")
#     st.markdown("🟣 **Records Officer** — LVA compliance liaison")
#     st.markdown("🟢 **Records Custodian** — Record storage")
#     st.divider()
#     st.caption("Powered by Ollama llama3 + NLP Fallback")

# ── STEP 1: UPLOAD ────────────────────────────────────────────────────────────
st.subheader("📎 Step 1 — Upload PDF Documents")

uploaded_files = st.file_uploader(
    "Upload Records Management PDFs",
    type=["pdf"],
    accept_multiple_files=True
)

if uploaded_files:
    cols = st.columns(min(len(uploaded_files), 4))
    for i, f in enumerate(uploaded_files):
        with cols[i % 4]:
            st.success(f"✅ {f.name}\n{round(f.size/1024/1024,1)} MB")

st.divider()

# ── STEP 2: ANALYZE ───────────────────────────────────────────────────────────
st.subheader("🚀 Step 2 — Run AI Analysis")

if not uploaded_files:
    st.warning("⬆️ Please upload PDF files above to begin.")
else:
    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        run = st.button("🤖 Run AI Analysis", use_container_width=True, type="primary")
    with col_info:
        if running and model_ok:
            st.info(f"🤖 Will use Ollama {OLLAMA_MODEL} LLM + NLP fallback")
        else:
            st.warning("⚠️ Ollama not ready — will use NLP fallback only. Setup Ollama in sidebar for better results.")

    if run:
        with st.spinner("📄 Reading PDFs..."):
            all_text = ""
            bar = st.progress(0, text="Reading PDFs...")
            for i, f in enumerate(uploaded_files):
                all_text += read_pdf(f)
                bar.progress((i+1)/len(uploaded_files), text=f"Reading: {f.name}")

        st.success(f"📄 Extracted {len(all_text):,} characters from {len(uploaded_files)} PDF(s)")

        with st.spinner("🤖 AI analyzing content — this may take 1-2 minutes..."):
            data  = hybrid_extract(all_text)
            df    = to_dataframe(data)
            stats = get_summary_stats(df)

        st.session_state["df"]       = df
        st.session_state["stats"]    = stats
        st.session_state["analyzed"] = True

        if len(df) == 0:
            st.error("❌ No data extracted. PDF may be image-based (scanned). Text-based PDFs work best.")
        else:
            st.success(f"✅ Found **{stats['total_departments']} departments** and **{stats['total_tools']} tools**")

st.divider()

# ── RESULTS ───────────────────────────────────────────────────────────────────
if st.session_state.get("analyzed") and "df" in st.session_state:
    df    = st.session_state["df"]
    stats = st.session_state["stats"]

    if df.empty:
        st.warning("No data to display. Please re-run analysis.")
        st.stop()

    # ── METRICS ───────────────────────────────────────────────────────────────
    st.subheader("📊 Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🏢 Departments",       stats["total_departments"])
    c2.metric("🛠️ Tools / Systems",   stats["total_tools"])
    c3.metric("🔗 Relationships",     stats["total_relationships"])
    c4.metric("👑 System Owners",     stats["relationship_breakdown"].get("System Owner", 0))
    st.divider()

    # ── TABLE ─────────────────────────────────────────────────────────────────
    st.subheader("📋 Extracted Data — All Departments & Tools")

    f1, f2 = st.columns(2)
    with f1:
        dept_filter = st.multiselect("Filter by Department",
                                     sorted(df["department"].unique()))
    with f2:
        rel_filter  = st.multiselect("Filter by Relationship",
                                     sorted(df["relationship"].unique()))

    fdf = df.copy()
    if dept_filter: fdf = fdf[fdf["department"].isin(dept_filter)]
    if rel_filter:  fdf = fdf[fdf["relationship"].isin(rel_filter)]

    def style_rel(val):
        m = {
            "System Owner":      "background-color:#003f5c;color:#00d4ff",
            "Workflow User":     "background-color:#5c2700;color:#ff6b35",
            "Records Officer":   "background-color:#2d0060;color:#b57bee",
            "Records Custodian": "background-color:#004d2e;color:#10b981",
        }
        return m.get(val, "")

    display = fdf[["department","tool","relationship","usage"]].copy()
    st.dataframe(display.style.map(style_rel, subset=["relationship"]),
                 use_container_width=True, height=350)
    st.caption(f"Showing {len(fdf)} of {len(df)} records")
    st.divider()

    # ── CHARTS ────────────────────────────────────────────────────────────────
    st.subheader("📈 Visual Analysis")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**🏢 Tools per Department**")
        dept_counts = df.groupby("department")["tool"].count().sort_values(ascending=True)
        fig, ax = plt.subplots(figsize=(8, max(4, len(dept_counts)*0.5)))
        fig.patch.set_facecolor('#0e1117')
        ax.set_facecolor('#0e1117')
        ax.barh(dept_counts.index, dept_counts.values, color="#00D4FF", alpha=0.85)
        for i, v in enumerate(dept_counts.values):
            ax.text(v+0.05, i, str(v), va='center', color='white', fontsize=9)
        ax.tick_params(colors='white', labelsize=8)
        ax.set_xlabel("Number of Tools", color='#aaa', fontsize=9)
        for sp in ax.spines.values(): sp.set_color('#333')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        plt.tight_layout()
        st.pyplot(fig); plt.close()

    with col2:
        st.markdown("**🔗 Relationship Distribution**")
        rel_counts  = df["relationship"].value_counts()
        colors_pie  = [COLORS.get(r, "#666") for r in rel_counts.index]
        fig2, ax2   = plt.subplots(figsize=(6,5))
        fig2.patch.set_facecolor('#0e1117')
        ax2.set_facecolor('#0e1117')
        _, texts, autotexts = ax2.pie(
            rel_counts.values, labels=rel_counts.index,
            colors=colors_pie, autopct='%1.0f%%', startangle=90,
            textprops={'color':'white','fontsize':10},
            wedgeprops={'edgecolor':'#0e1117','linewidth':2}
        )
        for at in autotexts: at.set_color('black'); at.set_fontweight('bold')
        plt.tight_layout()
        st.pyplot(fig2); plt.close()

    st.divider()

    # ── NETWORK GRAPH ─────────────────────────────────────────────────────────
    st.subheader("🕸️ Department → Tool Network Graph")
    st.caption("🔵 Blue = Department  |  🟢 Green = Tool  |  Edge color = Relationship type")

    G   = build_graph(df)
    pos = nx.spring_layout(G, k=2.5, iterations=60, seed=42)

    dept_nodes = [n for n,d in G.nodes(data=True) if d.get("type")=="department"]
    tool_nodes = [n for n,d in G.nodes(data=True) if d.get("type")=="tool"]
    edge_cols  = [COLORS.get(d.get("label",""),"#555") for _,_,d in G.edges(data=True)]

    fig3, ax3  = plt.subplots(figsize=(14,8))
    fig3.patch.set_facecolor('#0e1117')
    ax3.set_facecolor('#0e1117')
    nx.draw_networkx_nodes(G, pos, nodelist=dept_nodes,
                           node_color="#1E3A8A", node_size=3000, ax=ax3, alpha=0.95)
    nx.draw_networkx_nodes(G, pos, nodelist=tool_nodes,
                           node_color="#065F46", node_size=2000, ax=ax3, alpha=0.95)
    nx.draw_networkx_edges(G, pos, edge_color=edge_cols, width=2, alpha=0.7, ax=ax3,
                           arrows=True, arrowsize=15, connectionstyle='arc3,rad=0.1')
    nx.draw_networkx_labels(G, pos, font_color='white', font_size=9,
                            font_weight='bold', ax=ax3)
    ax3.legend(
        handles=[
            mpatches.Patch(color="#1E3A8A", label="Department"),
            mpatches.Patch(color="#065F46", label="Tool/System"),
            mpatches.Patch(color="#00D4FF", label="System Owner"),
            mpatches.Patch(color="#FF6B35", label="Workflow User"),
            mpatches.Patch(color="#7C3AED", label="Records Officer"),
            mpatches.Patch(color="#10B981", label="Records Custodian"),
        ],
        loc='upper left', facecolor='#1a1a2e',
        edgecolor='#333', labelcolor='white', fontsize=9
    )
    ax3.axis('off')
    plt.tight_layout()
    st.pyplot(fig3); plt.close()
    st.divider()

    # ── DEPT CARDS ────────────────────────────────────────────────────────────
    st.subheader("🏢 Department Detail Cards")
    depts = sorted(df["department"].unique())
    cols  = st.columns(3)
    icons = {
        "System Owner": "🔵", "Workflow User": "🟠",
        "Records Officer": "🟣", "Records Custodian": "🟢"
    }
    for i, dept in enumerate(depts):
        ddf     = df[df["department"] == dept]
        tools   = ddf["tool"].tolist()
        rel     = ddf["relationship"].mode()[0] if not ddf.empty else "Unknown"
        context = ddf["business_context"].iloc[0] if "business_context" in ddf.columns else ""
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"**📁 {dept}**")
                st.markdown(f"{icons.get(rel,'⚪')} `{rel}`")
                st.markdown(f"**Tools:** {' · '.join(tools)}")
                if context and context != "Unknown":
                    with st.expander("📄 Context from PDF"):
                        st.caption(context[:400])

    st.divider()

    # ── SUMMARY TABLES ────────────────────────────────────────────────────────
    st.subheader("📊 Relationship Breakdown")
    r1, r2 = st.columns(2)
    with r1:
        st.markdown("**By Relationship Type**")
        st.dataframe(
            df.groupby("relationship").agg(
                Departments=("department","nunique"),
                Tools=("tool","nunique"),
                Total=("tool","count")
            ).reset_index(),
            use_container_width=True
        )
    with r2:
        st.markdown("**By Department**")
        st.dataframe(
            df.groupby("department").agg(
                Tools=("tool","count"),
                Relationship=("relationship", lambda x: x.mode()[0])
            ).reset_index(),
            use_container_width=True
        )
    st.divider()

    # ── EXPORT ────────────────────────────────────────────────────────────────
    st.subheader("💾 Export Results")
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name="All Data", index=False)
        df.groupby("department")["tool"].apply(list).reset_index().to_excel(
            writer, sheet_name="By Department", index=False)
        df["relationship"].value_counts().reset_index().to_excel(
            writer, sheet_name="Relationships", index=False)

    d1, d2 = st.columns(2)
    with d1:
        st.download_button("📥 Download Excel",
                           buf.getvalue(),
                           "rm_analysis.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True, type="primary")
    with d2:
        st.download_button("📥 Download CSV",
                           df.to_csv(index=False),
                           "rm_analysis.csv", "text/csv",
                           use_container_width=True)

else:
    st.info("📄 Upload PDFs above and click **Run AI Analysis** to begin.")
    with st.expander("ℹ️ How it works"):
        st.markdown("""
**AI Pipeline:**
1. **PDF Reading** — PyMuPDF extracts text
2. **Ollama llama3** — LLM reads chunks and extracts departments + tools
3. **NLP Fallback** — Regex-based extraction runs in parallel
4. **Deduplicate** — Merges both results, removes duplicates
5. **Dashboard** — Charts, network graph, detail cards
6. **Export** — Excel + CSV download

**Ollama Setup** (sidebar):
- Click "Auto-Setup Ollama" — it downloads, installs, and pulls llama3 automatically
- First run downloads ~4GB model — takes 5-10 mins
- After that, all analysis is instant and 100% offline
        """)
