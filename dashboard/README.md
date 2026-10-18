# Tableau Public dashboard

Tableau Public cannot connect to DuckDB or Snowflake, so the dashboard reads CSV extracts:

```bash
make export-dashboard     # writes data/exports/*.csv from the marts and the ml schema
```

In Tableau Public Desktop: **Connect → Text file**, add each CSV as its own data source (no joins needed).

## Sheets

| # | Sheet | Source | Build |
|---|---|---|---|
| 1 | Daily volume and laundering share | `daily_volume.csv` | Dual axis. Bars: `tx_count` by `transaction_date` (day), log scale. Line: `laundering_share` on the right axis, formatted as %. Color bars by `is_simulation_tail` (grey for the tail) and add a caption: "Sep 11–18 is a laundering-only tail of the simulation and is excluded from modeling." |
| 2 | Laundering rate by payment format and currency | `laundering_by_format_currency.csv` | Highlight table. Rows `payment_format`, columns `payment_currency`. Color = SUM(`laundering_tx_count`) / SUM(`tx_count`) (calculated field), label = same, tooltip with `tx_count`. Sort formats by total rate. |
| 3 | Model comparison at the alert budget | `model_comparison.csv` | Horizontal bars: `caught` by `model`, sorted descending. Reference line at 3.2 labeled "random". Tooltip: `precision`, `recall`, `pr_auc`. Title: "Laundering accounts caught with 357 alerts (500/week)". |
| 4 | Alert capacity curve | `alert_capacity.csv` | Line: `caught` by `alerts`, color = `model`. Reference line at `alerts` = 357 labeled "budget". |
| 5 | Top flagged accounts | `top_flagged_accounts.csv` | Text table, top 25 by `score_rank`: `account_id`, `score`, `is_suspicious` (✓/✗), `tx_count`, `fan_out`, `fan_in`, `share_ach`, `share_cross_bank`, `flow_balance`. Color `is_suspicious`. |
| 6 | Typologies (optional) | `typology_summary.csv` | Bars: `attempts` and `usd_volume` by `typology`. |

## Layout

One dashboard, 1200 × 900:

```
┌──────────────────────────────┬──────────────────────────────┐
│ 1 Daily volume (full width)                                 │
├──────────────────────────────┬──────────────────────────────┤
│ 2 Rate by format × currency  │ 3 Model comparison at budget │
├──────────────────────────────┼──────────────────────────────┤
│ 4 Alert capacity curve       │ 5 Top flagged accounts       │
└──────────────────────────────┴──────────────────────────────┘
```

Add a text box at the top: "Synthetic data (IBM AML, HI-Small). Test window Sep 6–10, 2022.
Budget: 500 alerts/week = 357 per 5-day window."

Publish with **File → Save to Tableau Public**, then put the link in the main README.
