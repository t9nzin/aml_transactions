select
    account_id,
    min(bank) as bank,
    min(transaction_ts) as first_seen_ts,
    max(transaction_ts) as last_seen_ts,
    count(distinct transaction_id) as tx_count,
    max(case when is_laundering then 1 else 0 end) as ever_laundering
from {{ ref("int_account_transactions") }}
group by account_id
