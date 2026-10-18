with pattern_transactions as (

    select * from {{ ref("int_pattern_transactions") }}

),

amounts as (

    select transaction_id, amount_usd
    from {{ ref("int_transactions_usd") }}

)

select
    pattern_transactions.typology,
    count(distinct pattern_transactions.attempt_id) as attempts,
    count(*) as tx_count,
    count(pattern_transactions.transaction_id) as matched_tx_count,
    sum(amounts.amount_usd) as usd_volume,
    count(distinct pattern_transactions.from_account_id) as distinct_senders,
    count(distinct pattern_transactions.to_account_id) as distinct_receivers
from pattern_transactions
left join amounts
    on pattern_transactions.transaction_id = amounts.transaction_id
group by pattern_transactions.typology
