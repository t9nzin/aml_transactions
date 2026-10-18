select
    payment_format,
    payment_currency,
    count(*) as tx_count,
    sum(case when is_laundering then 1 else 0 end) as laundering_tx_count,
    avg(case when is_laundering then 1.0 else 0.0 end) as laundering_rate,
    sum(amount_usd) as usd_volume
from {{ ref("int_transactions_usd") }}
where {{ in_modeling_period("transaction_date") }}
group by payment_format, payment_currency
