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

def clean_dataframe(df):
    # 1. Remove empty column names
    df = df.loc[:, df.columns.notna()]
    df = df.loc[:, df.columns != ""]

    # 2. Fix duplicate column names
    df.columns = [f"{col}_{i}" if list(df.columns).count(col) > 1 else col
                  for i, col in enumerate(df.columns)]

    # 3. Remove fully empty columns
    df = df.dropna(axis=1, how="all")

    return df