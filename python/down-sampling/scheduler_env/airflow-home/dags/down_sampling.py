from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.hooks.base_hook import BaseHook
from datetime import datetime, timedelta
from downsampling_utils.multi import DataProcessor
import requests
import pendulum
import pytz


local_tz = pendulum.timezone("Asia/Seoul")

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 0,
}


def get_influxdb_seq(ti):
    try:
        connection = BaseHook.get_connection('o11y-manager')

        ip = connection.host
        port = connection.port
        api_url = f"http://{ip}:{port}/api/o11y/monitoring/influxdb"

        response = requests.get(api_url)
        response.raise_for_status()

        response_data = response.json()

        influxdb_list = response_data.get('data', [])
        seq_list = [entry['seq'] for entry in influxdb_list if 'seq' in entry]

        print(f"Extracted seq list: {seq_list}")

        ti.xcom_push(key='influxdb_seq_list', value=seq_list)

    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch InfluxDB list: {e}")
        raise


def data_down_sampling(ti, **context):
    exec_date = context['data_interval_start'] + timedelta(hours=1)
    pre_hour = context['data_interval_start']

    exec_date_utc = exec_date.astimezone(pytz.utc)
    pre_hour_utc = pre_hour.astimezone(pytz.utc)

    exec_time_str = exec_date_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
    pre_hour_time_str = pre_hour_utc.strftime('%Y-%m-%dT%H:%M:%SZ')

    seq_list = ti.xcom_pull(key='influxdb_seq_list', task_ids='call_influxdb_seq')

    data_processor = DataProcessor(output_db=seq_list, start=pre_hour_time_str, end=exec_time_str)
    data_processor.process_measurements()


with DAG(
    dag_id='down_sampling',
    default_args=default_args,
    description='A DAG to down-sample data',
    start_date=datetime(2024, 9, 12, tzinfo=local_tz),
    schedule_interval='* */1 * * *',
    catchup=False,
) as dag:
    call_influxdb_seq = PythonOperator(
        task_id='call_influxdb_seq',
        python_callable=get_influxdb_seq,
    )

    data_down_sampling = PythonOperator(
        task_id='data_down_sampling',
        python_callable=data_down_sampling,
    )

    call_influxdb_seq >> data_down_sampling


if __name__ == "__main__":
    dag.cli()
