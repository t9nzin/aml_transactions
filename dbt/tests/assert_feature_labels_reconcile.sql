-- Every laundering transfer in the modeling period must show up as a positive label on both
-- its sender's and its receiver's feature row. Returns windows whose positive counts disagree.

with expected as (

    select
        {{ window_start("transaction_date") }} as window_start,
        count(distinct account_id) as positive_accounts
    from {{ ref("int_account_transactions") }}
    where is_laundering and {{ in_modeling_period("transaction_date") }}
    group by 1

),

actual as (

    select window_start, sum(is_suspicious) as positive_accounts
    from {{ ref("fct_account_features") }}
    group by window_start

)

select expected.window_start, expected.positive_accounts as expected, actual.positive_accounts as actual
from expected
full outer join actual
    on expected.window_start = actual.window_start
where coalesce(expected.positive_accounts, -1) <> coalesce(actual.positive_accounts, -1)
