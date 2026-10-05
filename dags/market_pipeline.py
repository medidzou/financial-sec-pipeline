from datetime import datetime, timezone

import pandas as pd
from airflow import DAG
from airflow.operators.python import PythonOperator

from etl.extract import SYMBOLS, fetch_market_data
from etl.load import persist_pipeline_results
from etl.transform import clean_data, compute_indicators, validate_data


def dataframe_to_records(dataframe):
    records = []
    for record in dataframe.to_dict(orient="records"):
        serializable_record = {}
        for key, value in record.items():
            if pd.isna(value):
                serializable_record[key] = None
            elif hasattr(value, "isoformat"):
                serializable_record[key] = value.isoformat()
            elif hasattr(value, "item"):
                serializable_record[key] = value.item()
            else:
                serializable_record[key] = value
        records.append(serializable_record)
    return records


def extract_market_data():
    dataframe = fetch_market_data(SYMBOLS, period="5d")
    return dataframe_to_records(dataframe)


def transform_market_data(ti):
    raw_records = ti.xcom_pull(task_ids="extract")
    raw_dataframe = pd.DataFrame(raw_records or [])
    cleaned_dataframe = clean_data(raw_dataframe)
    clean_dataframe, rejected_dataframe = validate_data(cleaned_dataframe)
    enriched_dataframe = compute_indicators(clean_dataframe)
    return {
        "clean": dataframe_to_records(clean_dataframe),
        "enriched": dataframe_to_records(enriched_dataframe),
        "rejected": dataframe_to_records(rejected_dataframe),
    }


def load_market_data(ti):
    results = ti.xcom_pull(task_ids="transform") or {}
    persist_pipeline_results(
        pd.DataFrame(results.get("clean", [])),
        pd.DataFrame(results.get("enriched", [])),
        pd.DataFrame(results.get("rejected", [])),
    )


with DAG(
    dag_id="financial_market_pipeline",
    description="Extraction, validation et chargement quotidien des cours financiers.",
    start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
    schedule="0 6 * * *",
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2},
    tags=["finance", "etl"],
) as dag:
    extract_task = PythonOperator(
        task_id="extract",
        python_callable=extract_market_data,
    )
    transform_task = PythonOperator(
        task_id="transform",
        python_callable=transform_market_data,
    )
    load_task = PythonOperator(
        task_id="load",
        python_callable=load_market_data,
    )

    extract_task >> transform_task >> load_task