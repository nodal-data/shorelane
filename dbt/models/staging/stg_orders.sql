-- Orders, lightly cleaned. The raw table already carries the channel and the
-- net-vs-gross distinction that drives the five revenues.
--
-- Money columns go through the money() macro, which pins DECIMAL(38,9) using
-- whichever spelling the active warehouse accepts. See macros/money.sql -- a
-- bare `numeric` silently truncates cents on Redshift.
with source as (
    select * from {{ source('app_db', 'app_db__orders') }}
)
select
    order_id,
    customer_id,
    channel,
    cast(order_date as date)        as order_date,
    {{ money('gross_amount') }}     as gross_amount,
    take_rate,
    {{ money('net_amount') }}       as net_amount
from source
