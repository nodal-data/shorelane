{#
  money(column) -- cast a money column to DECIMAL(38,9) on any warehouse.

  Precision MUST be pinned, but the two warehouses disagree on how to say it,
  and each punishes the other's spelling:

    BigQuery  bare `numeric` IS decimal(38,9). Parameterized types are NOT
              allowed in CAST expressions -- `cast(x as numeric(38,9))` fails
              outright with "Parameterized types are not allowed in CAST
              expressions."

    Redshift  bare `numeric` is decimal(18,0). It does NOT error; it silently
              truncates every cent, which breaks parity with
              generators/measures.py and quietly invalidates all ground truth.

  So there is no single portable spelling -- one dialect errors loudly and the
  other is wrong in silence. This macro emits whichever literal means
  decimal(38,9) to the active target.

  Use this for every money column. Never write a bare `cast(... as numeric)`.
#}
{%- macro money(column) -%}
    {%- if target.type == 'bigquery' -%}
cast({{ column }} as numeric)
    {%- else -%}
cast({{ column }} as decimal(38,9))
    {%- endif -%}
{%- endmacro -%}
