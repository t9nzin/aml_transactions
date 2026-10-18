{#
    Each transfer seen from both ends: one 'out' row for the sender and one 'in' row for the
    receiver. Every account-level aggregate is built from this model.
    A self-transfer yields an 'out' and an 'in' row for the same account.
#}

with transactions as (

    select * from {{ ref("int_transactions_usd") }}

),

sides as (

    select
        transaction_id,
        transaction_ts,
        transaction_date,
        from_account_id as account_id,
        from_bank as bank,
        'out' as direction,
        to_account_id as counterparty_id,
        amount_usd,
        payment_format,
        is_cross_bank,
        is_cross_currency,
        is_self_transfer,
        is_laundering
    from transactions

    union all

    select
        transaction_id,
        transaction_ts,
        transaction_date,
        to_account_id as account_id,
        to_bank as bank,
        'in' as direction,
        from_account_id as counterparty_id,
        amount_usd,
        payment_format,
        is_cross_bank,
        is_cross_currency,
        is_self_transfer,
        is_laundering
    from transactions

)

select * from sides
