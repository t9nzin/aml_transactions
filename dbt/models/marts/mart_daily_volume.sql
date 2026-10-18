select
    transaction_date,
    count(*) as tx_count,
    sum(case when is_laundering then 1 else 0 end) as laundering_tx_count,
    avg(case when is_laundering then 1.0 else 0.0 end) as laundering_share,
    sum(amount_usd) as usd_volume,
    coalesce(sum(case when is_laundering then amount_usd end), 0) as laundering_usd_volume,
    -- Sep 11 onward is a laundering-only tail of the simulation, kept for transparency.
    not ({{ in_modeling_period("transaction_date") }}) as is_simulation_tail
from {{ ref("int_transactions_usd") }}
group by transaction_date
