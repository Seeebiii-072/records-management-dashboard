"""
graph_viz.py
============
1. clean_duplicates() — sentence-like / junk dept names remove karo
2. draw_better_graph() — bipartite layout: depts LEFT, tools RIGHT
"""

import re
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


COLORS = {
    "System Owner":      "#00D4FF",
    "Workflow User":     "#FF6B35",
    "Records Officer":   "#7C3AED",
    "Records Custodian": "#10B981",
}


# ── DUPLICATE / JUNK CLEANER ─────────────────────────────────────────────────
def clean_duplicates(df):
    """
    Remove:
    - Sentence-like dept names (too long, ends with ., has bullets)
    - Exact duplicates
    - Near-duplicate dept names (normalize and merge)
    """
    if df.empty:
        return df

    df = df.copy()

    def is_valid_dept(name):
        name = str(name).strip()
        if len(name) < 3 or len(name) > 70:
            return False
        if name.startswith(('•', '-', '*', '■', 'o ')):
            return False
        if name.endswith(('.', ',', ';')):
            return False
        # Sentences have many lowercase words
        words = name.split()
        if len(words) > 7:
            return False
        lowercase_ratio = sum(1 for w in words if w and w[0].islower()) / max(len(words), 1)
        if lowercase_ratio > 0.5 and len(words) > 3:
            return False
        # Starts with digit followed by space (like "20 Juvenile Justice") — keep
        # But pure numbers remove
        if re.match(r'^\d+$', name):
            return False
        return True

    # Filter valid depts
    df = df[df['department'].apply(is_valid_dept)].copy()

    # Normalize for dedup (lowercase, remove non-alphanumeric)
    def normalize(name):
        return re.sub(r'[^a-z0-9]', '', str(name).lower())

    # Keep first occurrence of each normalized name
    seen = {}
    canonical = {}
    for dept in df['department'].unique():
        norm = normalize(dept)
        if norm not in seen:
            seen[norm] = dept
        canonical[dept] = seen[norm]

    df['department'] = df['department'].map(canonical)

    # Final dedup
    df = df.drop_duplicates(subset=['department', 'tool'])
    df = df.reset_index(drop=True)

    return df


# ── BIPARTITE GRAPH ───────────────────────────────────────────────────────────
def draw_better_graph(df, ax=None):
    """
    Clean bipartite layout:
    - Departments → LEFT column
    - Tools       → RIGHT column
    - No overlapping labels
    - Color-coded edges by relationship
    """
    if df.empty:
        return

    depts = sorted(df['department'].unique().tolist())
    tools = sorted(df['tool'].unique().tolist())

    G = nx.Graph()
    for d in depts:
        G.add_node(d, node_type='department')
    for t in tools:
        G.add_node(t, node_type='tool')
    for _, row in df.iterrows():
        G.add_edge(
            row['department'], row['tool'],
            label=row.get('relationship', 'Workflow User')
        )

    # ── POSITIONS ─────────────────────────────────────────────────────────────
    pos = {}
    n_dept = len(depts)
    n_tool = len(tools)

    for i, d in enumerate(depts):
        y = 1.0 - (2.0 * i / max(n_dept - 1, 1))
        pos[d] = (-1.0, y)

    for i, t in enumerate(tools):
        y = 1.0 - (2.0 * i / max(n_tool - 1, 1))
        pos[t] = (1.0, y)

    # ── FIGURE ────────────────────────────────────────────────────────────────
    if ax is None:
        h = max(8, max(n_dept, n_tool) * 0.55)
        fig, ax = plt.subplots(figsize=(18, h))

    fig = ax.get_figure()
    fig.patch.set_facecolor('#0e1117')
    ax.set_facecolor('#0e1117')

    # ── EDGES ─────────────────────────────────────────────────────────────────
    edge_colors = [
        COLORS.get(G[u][v].get('label', ''), '#444444')
        for u, v in G.edges()
    ]
    nx.draw_networkx_edges(
        G, pos, ax=ax,
        edge_color=edge_colors,
        width=1.2, alpha=0.45,
        arrows=False
    )

    # ── DEPT NODES (left) ─────────────────────────────────────────────────────
    nx.draw_networkx_nodes(
        G, pos, ax=ax,
        nodelist=depts,
        node_color='#1E3A8A',
        node_size=500,
        alpha=0.95
    )

    # ── TOOL NODES (right) ────────────────────────────────────────────────────
    nx.draw_networkx_nodes(
        G, pos, ax=ax,
        nodelist=tools,
        node_color='#065F46',
        node_size=900,
        alpha=0.95
    )

    # ── DEPT LABELS (right-aligned, left of node) ─────────────────────────────
    for d in depts:
        x, y = pos[d]
        ax.text(
            x - 0.06, y, d,
            color='white', fontsize=6.5,
            ha='right', va='center',
            fontweight='normal'
        )

    # ── TOOL LABELS (left-aligned, right of node) ─────────────────────────────
    for t in tools:
        x, y = pos[t]
        ax.text(
            x + 0.06, y, t,
            color='#10B981', fontsize=8,
            ha='left', va='center',
            fontweight='bold'
        )

    # ── COLUMN HEADERS ────────────────────────────────────────────────────────
    ax.text(-1.0,  1.12, '🏢  DEPARTMENTS',
            color='#00D4FF', fontsize=11, fontweight='bold',
            ha='center', va='center')
    ax.text( 1.0,  1.12, 'TOOLS / SYSTEMS  🛠️',
            color='#10B981', fontsize=11, fontweight='bold',
            ha='center', va='center')

    # ── CENTER DIVIDER ────────────────────────────────────────────────────────
    ax.axvline(x=0, color='#1e2d45', linewidth=1,
               linestyle='--', alpha=0.4)

    # ── LEGEND ────────────────────────────────────────────────────────────────
    legend_handles = [
        mpatches.Patch(color='#1E3A8A', label='Department'),
        mpatches.Patch(color='#065F46', label='Tool / System'),
        mpatches.Patch(color='#00D4FF', label='System Owner'),
        mpatches.Patch(color='#FF6B35', label='Workflow User'),
        mpatches.Patch(color='#7C3AED', label='Records Officer'),
        mpatches.Patch(color='#10B981', label='Records Custodian'),
    ]
    ax.legend(
        handles=legend_handles,
        loc='lower center',
        ncol=3,
        facecolor='#111827',
        edgecolor='#1e2d45',
        labelcolor='white',
        fontsize=8,
        bbox_to_anchor=(0.5, -0.06)
    )

    ax.set_xlim(-1.7, 1.7)
    ax.set_ylim(-1.25, 1.25)
    ax.axis('off')
    ax.set_title(
        'Department  →  Tool  Relationship Network',
        color='white', fontsize=13, fontweight='bold', pad=16
    )

    plt.tight_layout()