# LookML as a CONTEXT ARTIFACT (authored, not rendered).
#
# Looker (core) is a $60k+/yr enterprise platform — we do NOT run an instance.
# But LookML is just text, and it IS a semantic layer: exactly the kind of context
# surface Nodal reads from and evaluates against. Authoring it here lets us demo
# "Nodal interoperating with a customer's LookML" without paying for Looker.
#
# Render dashboards with Looker Studio (free, BigQuery-native) or bi/plotly instead.

view: fct_revenue {
  sql_table_name: shorelane.fct_revenue ;;

  dimension: activity_date {
    type: date
    sql: ${TABLE}.activity_date ;;
  }

  dimension: measure_name {
    type: string
    sql: ${TABLE}.measure_name ;;
    description: "One of five revenues. There is no single 'revenue' — see Nodal context."
  }

  # Each measure is filtered to its own measure_name so the five never silently
  # collapse into one ambiguous SUM. This encodes the disambiguation in LookML.
  measure: gmv {
    type: sum
    sql: ${TABLE}.amount ;;
    filters: [measure_name: "gmv"]
  }
  measure: net_revenue {
    type: sum
    sql: ${TABLE}.amount ;;
    filters: [measure_name: "net_revenue"]
  }
  measure: recognized_revenue {
    type: sum
    sql: ${TABLE}.amount ;;
    filters: [measure_name: "recognized_revenue"]
    description: "CFO's number. GAAP. The canonical default for 'revenue'."
  }
  measure: billed_revenue {
    type: sum
    sql: ${TABLE}.amount ;;
    filters: [measure_name: "billed_revenue"]
  }
  measure: collected_cash {
    type: sum
    sql: ${TABLE}.amount ;;
    filters: [measure_name: "collected_cash"]
  }
}
