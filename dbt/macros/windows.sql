{# Tumbling feature windows of var('window_days') days, starting at var('modeling_start').
   Dates outside the modeling period get a null window. #}

{% macro modeling_start() -%}
    cast('{{ var("modeling_start") }}' as date)
{%- endmacro %}

{% macro in_modeling_period(date_col) -%}
    {{ date_col }} between cast('{{ var("modeling_start") }}' as date)
        and cast('{{ var("modeling_end") }}' as date)
{%- endmacro %}

{% macro window_start(date_col) -%}
    cast({{ dbt.dateadd(
        "day",
        "cast(floor(" ~ dbt.datediff(modeling_start(), date_col, "day") ~ " / " ~ var("window_days") ~ ") as integer) * " ~ var("window_days"),
        modeling_start()
    ) }} as date)
{%- endmacro %}
