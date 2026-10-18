import pandas as pd

from aml.graph import graph_features


def test_cycles_round_trips_and_scc_sizes():
    edges = pd.DataFrame(
        [
            ("a", "b"), ("b", "a"),              # round trip
            ("c", "d"), ("d", "e"), ("e", "c"),  # 3-cycle
            ("f", "g"),                          # no cycle
        ],
        columns=["from_account_id", "to_account_id"],
    )
    feats = graph_features(edges).set_index("account_id")
    assert feats.loc[["a", "b"], "round_trip"].tolist() == [1, 1]
    assert feats.loc[["c", "d", "e"], "round_trip"].tolist() == [0, 0, 0]
    assert feats.loc[["a", "c", "e"], "in_short_cycle"].tolist() == [1, 1, 1]
    assert feats.loc[["f", "g"], "in_short_cycle"].tolist() == [0, 0]
    assert feats.loc[["a", "c", "f"], "scc_size"].tolist() == [2, 3, 1]
