# Raw landing schema — revenue slice

Fivetran-shaped landing tables emitted by `generators/`. Documented here so the
mess is auditable: every column that drives the five-revenues divergence is called
out. As you add source systems (Salesforce, Shopify, ad platforms, Zendesk) and
the rest of the debt catalog, document them here too.

## app_db__orders
One row per order. The `channel` + `gross_amount`/`net_amount` split is the wedge.

| column | type | notes |
|---|---|---|
| order_id | string | PK |
| customer_id | string | FK to customers (not in this slice yet) |
| channel | string | `d2c` / `business_subscription` / `marketplace` |
| order_date | date | |
| gross_amount | numeric | full ticket; marketplace = full retail price |
| take_rate | float | marketplace only (0.15–0.25), else null |
| net_amount | numeric | what Shorelane earns; marketplace = gross × take_rate |

## app_db__invoices
Business-subscription net-30 billing. `collected_date` null = bad debt.

| column | type | notes |
|---|---|---|
| invoice_id | string | PK |
| order_id | string | FK |
| billed_date | date | = order_date (billed up front) |
| due_date | date | billed_date + 30 |
| collected_date | date | nullable; null = never collected |
| amount | numeric | = order net_amount |
| is_bad_debt | bool | |

## app_db__revenue_recognition
Ratable schedule. Subscriptions → 12 monthly rows; d2c/marketplace → 1 row at order date.

| column | type | notes |
|---|---|---|
| order_id | string | FK |
| recognition_date | date | month-stepped for subs |
| amount | numeric | monthly portion (subs) or full net (others) |

## stripe__refunds
Refunds on d2c + marketplace, lagged 3–45 days after the order.

| column | type | notes |
|---|---|---|
| refund_id | string | PK |
| order_id | string | FK |
| refund_date | date | order_date + lag |
| refund_amount | numeric | = order net_amount |
