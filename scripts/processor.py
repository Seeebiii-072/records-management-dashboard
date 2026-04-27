"""processor.py — DataFrame cleaner"""
import pandas as pd

def to_dataframe(data):
    if not data:
        return pd.DataFrame(columns=["department","tool","relationship","usage","business_context"])
    df = pd.DataFrame(data)
    for col in ["department","tool","relationship","usage","business_context"]:
        if col not in df.columns:
            df[col] = "Unknown"
    df["department"] = df["department"].str.strip()
    df["tool"]       = df["tool"].str.strip()
    df.drop_duplicates(subset=["department","tool"], inplace=True)
    df.fillna("Unknown", inplace=True)
    df = df[df["department"] != ""].reset_index(drop=True)
    return df

def get_summary_stats(df):
    return {
        "total_departments":      df["department"].nunique(),
        "total_tools":            df["tool"].nunique(),
        "total_relationships":    len(df),
        "relationship_breakdown": df["relationship"].value_counts().to_dict(),
    }
