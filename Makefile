# Shorelane build pipeline. `make help` for targets.

.PHONY: help install install-bq install-redshift generate verify load-bq load-redshift dbt dashboard biz-dashboard validate-dashboard clean

help:
	@grep -E '^[a-zA-Z_-]+:.*?# .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN{FS=":.*?# "}{printf "  %-14s %s\n", $$1, $$2}'

install: # install core + Plotly BI deps (verify/generate/dashboard run after this)
	pip install -e ".[bi]"

install-bq: # extra deps for the BigQuery loader + dbt (only needed to load/model)
	pip install -e ".[bigquery,dbt]"

install-redshift: # extra deps for the Redshift loader
	pip install -e ".[redshift]"

generate: # generate raw Parquet into data/raw
	python -m generators.emit

verify: # generate + print the five revenues for the target period
	python -m generators.emit --period

load-bq: # load raw Parquet into BigQuery (set PROJECT=...)
	python -m loaders.bigquery_load --project $(PROJECT)

load-redshift: # load raw Parquet into Redshift (set BUCKET=... COPY_ROLE_ARN=... [AS_OF=...])
	python -m loaders.redshift_load --bucket $(BUCKET) --copy-role-arn $(COPY_ROLE_ARN) \
		$(if $(AS_OF),--as-of $(AS_OF),)

dbt: # run staging + marts (requires ~/.dbt/profiles.yml)
	cd dbt && dbt run

dashboard: # render the free static Plotly dashboard (five revenues)
	python -m bi.plotly.revenue_dashboard

biz-dashboard: # launch the interactive exec dashboard at localhost:8050
	python -m bi.plotly.business_dashboard

validate-dashboard: # print the source-of-truth KPIs to validate against
	python -m bi.dashboard_data

clean: # remove generated artifacts
	rm -rf data/raw/*.parquet dbt/target bi/plotly/*.html
