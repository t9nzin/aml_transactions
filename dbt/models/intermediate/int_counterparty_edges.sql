{# Directed sender -> receiver edges with volume, the input for graph features. Self-transfers excluded. #}

select
    from_account_id,
    to_account_id,
    count(*) as tx_count,
    sum(amount_usd) as usd_total,
    min(transaction_ts) as first_ts,
    max(transaction_ts) as last_ts,
    sum(case when is_laundering then 1 else 0 end) as laundering_tx_count
from {{ ref("int_transactions_usd") }}
where not is_self_transfer
group by from_account_id, to_account_id
