from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.hooks.base_hook import BaseHook
import pendulum
from datetime import datetime
import requests
import pandas as pd
from sqlalchemy import create_engine, text


# Constants
API_BASE_URL = "http://192.168.130.210:18080/api/v1/agent/influxdb/list"
DB_CONN_ID = 'mcmp'
local_tz = pendulum.timezone("Asia/Seoul")

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
}


def get_data():
    response = requests.get(API_BASE_URL).json()
    data = response['data']
    save_to_mariadb(data)


def save_to_mariadb(data):
    # Convert the data into a pandas DataFrame
    data = pd.DataFrame(data)
    # Get database connection details from Airflow connection
    connection = BaseHook.get_connection(DB_CONN_ID)
    conn_string = f"mysql+mysqlconnector://{connection.login}:{connection.password}@{connection.host}:{connection.port}/{connection.schema}"
    engine = create_engine(conn_string)

    # Replace the existing table with the DataFrame
    with engine.connect() as conn:
        # Delete existing data
        conn.execute(text("DELETE FROM db_info"))

        # Insert new data
        data.to_sql('db_info', con=conn, if_exists='append', index=False)


dag = DAG(
    'get_db_info',
    default_args=default_args,
    description='',
    schedule_interval='@hourly',
    start_date=datetime(2024, 5, 22, tzinfo=local_tz),
    catchup=False,
)

with dag:
    get_data_task = PythonOperator(
        task_id='get_data_task',
        python_callable=get_data,
    )


if __name__ == "__main__":
    dag.cli()
