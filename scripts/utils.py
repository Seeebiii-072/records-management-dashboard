"""utils.py — Network graph builder"""
import networkx as nx

def build_graph(df):
    G = nx.Graph()
    for _, row in df.iterrows():
        dept = row["department"]
        tool = row["tool"]
        rel  = row.get("relationship","Workflow User")
        G.add_node(dept, type="department")
        G.add_node(tool, type="tool")
        G.add_edge(dept, tool, label=rel)
    return G
