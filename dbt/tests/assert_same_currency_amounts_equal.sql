-- When no conversion happens, the amount paid must equal the amount received.
select transaction_id, amount_paid, amount_received
from {{ ref("stg_transactions") }}
where payment_currency = receiving_currency
    and amount_paid <> amount_received
