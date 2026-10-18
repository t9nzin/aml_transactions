select
    attempt_id,
    lower(replace(typology, '-', '_')) as typology,
    typology_detail,
    transaction_ts,
    from_bank || '-' || from_account as from_account_id,
    to_bank || '-' || to_account as to_account_id,
    amount_paid,
    payment_currency as payment_currency_name,
    amount_received,
    lower(replace(payment_format, ' ', '_')) as payment_format
from {{ source("raw", "laundering_patterns") }}
