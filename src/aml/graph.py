"""Graph features per feature window: round-tripping and short cycles.

Cycles are only searched inside non-trivial strongly connected components (an account can only
sit on a cycle if it is in one), which shrinks the graph by about two orders of magnitude.
"""

from datetime import date

import networkx as nx
import pandas as pd

from aml import io

MAX_CYCLE_LENGTH = 4


def window_edges(start: date, end: date) -> pd.DataFrame:
    return io.read_sql(
        f"""
        select from_account_id, to_account_id
        from intermediate.int_transactions_usd
        where not is_self_transfer
            and transaction_date between '{start.isoformat()}' and '{end.isoformat()}'
        group by from_account_id, to_account_id
        """
    )


def graph_features(edges: pd.DataFrame) -> pd.DataFrame:
    """Per account: scc_size, round_trip (A->B and B->A) and in_short_cycle (length 2-4)."""
    graph = nx.from_pandas_edgelist(
        edges, "from_account_id", "to_account_id", create_using=nx.DiGraph
    )
    scc_size, cycle_nodes, round_trip_nodes = {}, set(), set()
    for component in nx.strongly_connected_components(graph):
        if len(component) == 1:
            continue
        for node in component:
            scc_size[node] = len(component)
        for cycle in nx.simple_cycles(graph.subgraph(component), length_bound=MAX_CYCLE_LENGTH):
            cycle_nodes.update(cycle)
            if len(cycle) == 2:
                round_trip_nodes.update(cycle)

    accounts = pd.Index(list(graph.nodes), name="account_id")
    return pd.DataFrame(
        {
            "scc_size": accounts.map(lambda a: scc_size.get(a, 1)),
            "round_trip": accounts.isin(round_trip_nodes).astype(int),
            "in_short_cycle": accounts.isin(cycle_nodes).astype(int),
        },
        index=accounts,
    ).reset_index()


def add_graph_features(df: pd.DataFrame) -> pd.DataFrame:
    """Join graph features onto the feature mart, window by window."""
    parts = []
    for (start, end), window in df.groupby(["window_start", "window_end"], sort=True):
        feats = graph_features(window_edges(start, end))
        parts.append(window.merge(feats, on="account_id", how="left"))
    out = pd.concat(parts, ignore_index=True)
    # Accounts with only self-transfers never enter the graph.
    out["scc_size"] = out["scc_size"].fillna(1).astype(int)
    out[["round_trip", "in_short_cycle"]] = out[["round_trip", "in_short_cycle"]].fillna(0).astype(int)
    return out
