{{
    config(
        materialized="incremental",
        incremental_strategy="delete+insert",
        unique_key="transaction_date",
        on_schema_change="fail",
    )
}}

{#
    Incremental by day. unique_key = transaction_date makes delete+insert replace whole days,
    so a reloaded partition overwrites its date cleanly (rows removed upstream disappear too).
    - Airflow passes run_date and rebuilds exactly that day.
    - Without run_date, the last loaded day is rebuilt along with anything newer.
#}

with source as (

    select * from {{ source("raw", "transactions") }}
    {% if is_incremental() %}
        {% if var("run_date") %}
    where transaction_date = cast('{{ var("run_date") }}' as date)
        {% else %}
    where transaction_date >= (select max(transaction_date) from {{ this }})
        {% endif %}
    {% endif %}

),

currencies as (

    select * from {{ ref("currency_codes") }}

)

select
    source.transaction_id,
    source.transaction_ts,
    source.transaction_date,
    source.from_bank,
    source.to_bank,
    source.from_bank || '-' || source.from_account as from_account_id,
    source.to_bank || '-' || source.to_account as to_account_id,
    source.amount_paid,
    paid.currency_code as payment_currency,
    source.amount_received,
    received.currency_code as receiving_currency,
    lower(replace(source.payment_format, ' ', '_')) as payment_format,
    source.is_laundering = 1 as is_laundering,
    source.from_bank <> source.to_bank as is_cross_bank,
    source.payment_currency <> source.receiving_currency as is_cross_currency,
    source.from_bank = source.to_bank and source.from_account = source.to_account as is_self_transfer,
    source.source_file,
    source.loaded_at
from source
left join currencies as paid
    on source.payment_currency = paid.currency_name
left join currencies as received
    on source.receiving_currency = received.currency_name
