-- Ratable recognition schedule. Subscriptions spread over the term; d2c and
-- marketplace recognized immediately (single row at order date).
--
-- Money columns go through the money() macro -- see macros/money.sql.
with source as (
    select * from {{ source('app_db', 'app_db__revenue_recognition') }}
)
select
    order_id,
    cast(recognition_date as date)  as recognition_date,
    {{ money('amount') }}           as amount
from source
