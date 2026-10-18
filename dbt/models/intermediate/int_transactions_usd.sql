{{ config(materialized="view") }}

select
    transactions.*,
    transactions.amount_paid * rates.usd_per_unit as amount_usd
from {{ ref("stg_transactions") }} as transactions
left join {{ ref("int_currency_rates") }} as rates
    on transactions.payment_currency = rates.currency_code
