import json
import requests
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.providers.mysql.hooks.mysql import MySqlHook
from datetime import datetime, timedelta
import pandas as pd
import pendulum
from downsampling_utils.multi import DataProcessor
from datetime import datetime
import pytz


# Constants
API_BASE_URL = "http://192.168.130.210:18080/api/v1/agent"
DB_CONN_ID = 'mcmp'
TABLE_NAME = 'db_info'
local_tz = pendulum.timezone("Asia/Seoul")

# Default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
}


def retrieve_data_from_db():
    """
    Retrieves data from the MariaDB database and returns it as a JSON string.
    """
    mysql_hook = MySqlHook(mysql_conn_id=DB_CONN_ID)
    sql = f"SELECT * FROM {TABLE_NAME};"
    df = mysql_hook.get_pandas_df(sql)
    return df.to_json()


def generate_api_urls(ti):
    """
    Generates API URLs based on the retrieved database information.
    """
    df_json = ti.xcom_pull(task_ids='retrieve_data_from_db')
    df = pd.read_json(df_json)

    urls = [generate_url(row) for _, row in df.iterrows()]

    ti.xcom_push(key='api_urls', value=urls)


def generate_url(row):
    """
    Generates an API URL for a given row of the DataFrame.
    """
    return (f"{API_BASE_URL}/influxdb/fields/{row['SEQ']}")


def call_api_list(ti, **context):
    """
    Calls the generated API URLs and updates the DataFrame with the extracted keys.
    """
    urls = ti.xcom_pull(key='api_urls', task_ids='generate_api_urls')
    df_json = ti.xcom_pull(task_ids='retrieve_data_from_db')
    df = pd.read_json(df_json)

    extracted_measurements_list = []
    for url in urls:
        try:
            print(url)
            response = requests.get(url)
            response.raise_for_status()
            response_json = response.json()
            # print(response_json)
            data = response_json.get("data", [])
            # print(data)
            measurements = [item['measurement'] for item in data]
            extracted_measurements_list.append(measurements)
        except requests.RequestException as e:
            extracted_measurements_list.append([])

    df['MEASUREMENTS'] = extracted_measurements_list
    ti.xcom_push(key='updated_df', value=df.to_json())


def get_miningdb_info(ti):
    url = API_BASE_URL + '/miningdb'
    response = requests.get(url).json()
    print(response)
    data = response['data']
    ti.xcom_push(key='miningdb_info', value=data)


def data_down_sampling(ti, **context):
    exec_date = context['data_interval_start'] + timedelta(hours=1)
    pre_hour = context['data_interval_start']

    exec_date_utc = exec_date.astimezone(pytz.utc)
    pre_hour_utc = pre_hour.astimezone(pytz.utc)

    exec_time_str = exec_date_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
    pre_hour_time_str = pre_hour_utc.strftime('%Y-%m-%dT%H:%M:%SZ')

    print(f"Execution Time: {exec_time_str}")
    print(f"Previous  Hour Time: {pre_hour_time_str}")

    miningdb_info = ti.xcom_pull(key='miningdb_info', task_ids='call_miningdb_info')
    df_json = ti.xcom_pull(key='updated_df', task_ids='call_api_list')
    df = pd.read_json(df_json)

    data_processor = DataProcessor(output_db=miningdb_info, input_db=df, start=pre_hour_time_str, end=exec_time_str)
    data_processor.process_measurements()


dag = DAG(
    'down_sampling',
    default_args=default_args,
    description='A DAG to down-sample data from MariaDB and make API calls',
    schedule_interval='@hourly',
    start_date=datetime(2024, 5, 22, tzinfo=local_tz),
    catchup=False,
)

with dag:
    retrieve_data_task = PythonOperator(
        task_id='retrieve_data_from_db',
        python_callable=retrieve_data_from_db,
    )

    generate_urls_task = PythonOperator(
        task_id='generate_api_urls',
        python_callable=generate_api_urls,
    )

    call_api_task = PythonOperator(
        task_id='call_api_list',
        python_callable=call_api_list,
    )

    call_miningdb_info = PythonOperator(
        task_id='call_miningdb_info',
        python_callable=get_miningdb_info,
    )

    data_down_sampling = PythonOperator(
        task_id='data_down_sampling',
        python_callable=data_down_sampling,
    )

    retrieve_data_task >> generate_urls_task >> call_api_task >> call_miningdb_info >> data_down_sampling

if __name__ == "__main__":
    dag.cli()
