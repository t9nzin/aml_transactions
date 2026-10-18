select
    account_id,
    transaction_date,
    sum(case when direction = 'out' then 1 else 0 end) as tx_out_count,
    sum(case when direction = 'in' then 1 else 0 end) as tx_in_count,
    coalesce(sum(case when direction = 'out' then amount_usd end), 0) as usd_out_total,
    coalesce(sum(case when direction = 'in' then amount_usd end), 0) as usd_in_total,
    count(distinct case when direction = 'out' and not is_self_transfer then counterparty_id end)
        as distinct_counterparties_out,
    count(distinct case when direction = 'in' and not is_self_transfer then counterparty_id end)
        as distinct_counterparties_in,
    sum(case when is_laundering then 1 else 0 end) as laundering_tx_count
from {{ ref("int_account_transactions") }}
group by account_id, transaction_date
