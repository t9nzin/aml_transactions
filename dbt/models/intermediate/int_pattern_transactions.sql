{#
    Attach transaction_id to each laundering-attempt row by matching the natural fields.
    The patterns file does not carry ids; timestamp + accounts + amount + format identifies a transfer.
#}

with patterns as (

    select * from {{ ref("stg_laundering_patterns") }}

),

transactions as (

    select * from {{ ref("stg_transactions") }}
    where is_laundering

)

select
    patterns.attempt_id,
    patterns.typology,
    patterns.typology_detail,
    transactions.transaction_id,
    patterns.transaction_ts,
    patterns.from_account_id,
    patterns.to_account_id,
    patterns.amount_paid
from patterns
left join transactions
    on patterns.transaction_ts = transactions.transaction_ts
    and patterns.from_account_id = transactions.from_account_id
    and patterns.to_account_id = transactions.to_account_id
    and patterns.amount_paid = transactions.amount_paid
    and patterns.payment_format = transactions.payment_format
