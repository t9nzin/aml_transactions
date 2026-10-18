{#
    USD value of one unit of each currency, derived from the data itself: the median of
    amount_received / amount_paid over transfers paid in that currency and received in USD.
    The median ignores the odd outlier transfer. USD is pinned to 1.
#}

with usd_conversions as (

    select
        payment_currency as currency_code,
        amount_received / amount_paid as usd_per_unit
    from {{ ref("stg_transactions") }}
    where receiving_currency = 'USD'
        and payment_currency <> 'USD'
        and amount_paid > 0

)

select
    currency_code,
    median(usd_per_unit) as usd_per_unit,
    count(*) as n_observations
from usd_conversions
group by currency_code

union all

select 'USD' as currency_code, 1.0 as usd_per_unit, null as n_observations
