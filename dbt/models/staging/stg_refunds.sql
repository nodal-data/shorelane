-- Refunds, lagged after the original order. Reduce net_revenue and collected_cash.
with source as (
    select * from {{ source('stripe', 'stripe__refunds') }}
)
select
    refund_id,
    order_id,
    cast(refund_date as date)    as refund_date,
    cast(refund_amount as numeric) as refund_amount
from source
