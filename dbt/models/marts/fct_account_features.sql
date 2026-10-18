{#
    One row per account per feature window (tumbling windows of var('window_days') days over the
    modeling period). Features and the label come from the same window: the model scores what an
    account did during the window, the way a monitoring team reviews last period's activity.

    Columns prefixed label_ are outcomes, never features.
#}

{% set payment_formats = ["ach", "bitcoin", "cash", "cheque", "credit_card", "reinvestment", "wire"] %}
{% set window_minutes = var("window_days") * 1440 %}

with sides as (

    select
        *,
        {{ window_start("transaction_date") }} as window_start
    from {{ ref("int_account_transactions") }}
    where {{ in_modeling_period("transaction_date") }}

),

-- A self-transfer appears twice (out and in); timing features count it once.
events as (

    select distinct account_id, window_start, transaction_id, transaction_ts
    from sides

),

gaps as (

    select
        account_id,
        window_start,
        {{ dbt.datediff(
            "lag(transaction_ts) over (partition by account_id, window_start order by transaction_ts)",
            "transaction_ts",
            "minute"
        ) }} as gap_minutes
    from events

),

gap_stats as (

    select
        account_id,
        window_start,
        avg(gap_minutes) as mean_gap_minutes,
        min(gap_minutes) as min_gap_minutes
    from gaps
    group by account_id, window_start

),

hourly as (

    select
        account_id,
        window_start,
        {{ dbt.date_trunc("hour", "transaction_ts") }} as hour_start,
        count(*) as tx_in_hour
    from events
    group by account_id, window_start, {{ dbt.date_trunc("hour", "transaction_ts") }}

),

burst as (

    select
        account_id,
        window_start,
        max(tx_in_hour) as max_tx_per_hour,
        count(*) as active_hours
    from hourly
    group by account_id, window_start

),

activity as (

    select
        account_id,
        window_start,
        min(bank) as bank,
        count(distinct transaction_id) as tx_count,
        sum(case when direction = 'out' then 1 else 0 end) as tx_out_count,
        sum(case when direction = 'in' then 1 else 0 end) as tx_in_count,

        coalesce(sum(case when direction = 'out' then amount_usd end), 0) as usd_out_total,
        coalesce(sum(case when direction = 'in' then amount_usd end), 0) as usd_in_total,
        coalesce(avg(case when direction = 'out' then amount_usd end), 0) as usd_out_mean,
        coalesce(avg(case when direction = 'in' then amount_usd end), 0) as usd_in_mean,
        coalesce(max(case when direction = 'out' then amount_usd end), 0) as usd_out_max,
        coalesce(max(case when direction = 'in' then amount_usd end), 0) as usd_in_max,

        count(distinct case when direction = 'out' and not is_self_transfer then counterparty_id end)
            as fan_out,
        count(distinct case when direction = 'in' and not is_self_transfer then counterparty_id end)
            as fan_in,

        avg(case when is_cross_bank then 1.0 else 0.0 end) as share_cross_bank,
        avg(case when is_cross_currency then 1.0 else 0.0 end) as share_cross_currency,
        avg(case when is_self_transfer then 1.0 else 0.0 end) as share_self_transfer,
        {% for fmt in payment_formats %}
        avg(case when payment_format = '{{ fmt }}' then 1.0 else 0.0 end) as share_{{ fmt }},
        {% endfor %}
        mode(payment_format) as dominant_payment_format,
        count(distinct transaction_date) as active_days,

        max(case when is_laundering then 1 else 0 end) as is_suspicious,
        count(distinct case when is_laundering then transaction_id end) as label_laundering_tx_count

    from sides
    group by account_id, window_start

)

select
    activity.account_id,
    activity.window_start,
    cast({{ dbt.dateadd("day", var("window_days") - 1, "activity.window_start") }} as date) as window_end,
    activity.bank,

    activity.tx_count,
    activity.tx_out_count,
    activity.tx_in_count,
    activity.usd_out_total,
    activity.usd_in_total,
    activity.usd_out_mean,
    activity.usd_in_mean,
    activity.usd_out_max,
    activity.usd_in_max,

    activity.fan_out,
    activity.fan_in,

    activity.share_cross_bank,
    activity.share_cross_currency,
    activity.share_self_transfer,
    {% for fmt in payment_formats %}
    activity.share_{{ fmt }},
    {% endfor %}
    activity.dominant_payment_format,

    -- Pass-through: money that comes in and leaves again. The ratio is unbounded (null when
    -- nothing came in); flow_balance is min/max of the two flows, in [0, 1], 1 = all of it passed through.
    activity.usd_out_total / nullif(activity.usd_in_total, 0) as pass_through_ratio,
    case
        when greatest(activity.usd_out_total, activity.usd_in_total) = 0 then 0
        else least(activity.usd_out_total, activity.usd_in_total)
            / greatest(activity.usd_out_total, activity.usd_in_total)
    end as flow_balance,

    -- Burstiness. With fewer than two transfers there is no gap: use the full window length.
    burst.max_tx_per_hour,
    burst.active_hours,
    activity.active_days,
    coalesce(gap_stats.mean_gap_minutes, {{ window_minutes }}) as mean_gap_minutes,
    coalesce(gap_stats.min_gap_minutes, {{ window_minutes }}) as min_gap_minutes,

    activity.is_suspicious,
    activity.label_laundering_tx_count

from activity
inner join burst
    on activity.account_id = burst.account_id
    and activity.window_start = burst.window_start
inner join gap_stats
    on activity.account_id = gap_stats.account_id
    and activity.window_start = gap_stats.window_start
