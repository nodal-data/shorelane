-- Orders, lightly cleaned. The raw table already carries the channel and the
-- net-vs-gross distinction that drives the five revenues.
with source as (
    select * from {{ source('app_db', 'app_db__orders') }}
)
select
    order_id,
    customer_id,
    channel,
    cast(order_date as date)              as order_date,
    cast(gross_amount as numeric)         as gross_amount,
    take_rate,
    cast(net_amount as numeric)           as net_amount
from source
