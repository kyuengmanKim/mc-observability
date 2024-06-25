from urllib.parse import urlparse
import pandas as pd
from influxdb import InfluxDBClient, exceptions
import pytz


kst = pytz.timezone('Asia/Seoul')


class InfluxDBConn:
    def __init__(self, id_connection_data):
        self.client = self.create_client(id_connection_data=id_connection_data)

    def create_client(self, id_connection_data):
        parsed_url = urlparse(id_connection_data.url)
        host = parsed_url.hostname
        port = parsed_url.port
        username = id_connection_data.username
        password = id_connection_data.password
        database = id_connection_data.database

        self.database = database
        self.policy = id_connection_data.retentionPolicy

        client = self.validate_db_credentials(username, password, database, host, port)

        return client

    def get_dataframe(self, query_string):
        result = self.client.query(query_string)
        output = []
        for key, values in result.items():
            resource_type = key[0]
            uuid = key[1]['uuid']
            for item in values:
                item['uuid'] = uuid
                item['resource_id'] = f"{resource_type}_usage"
                output.append(item)

        df = pd.DataFrame(output)
        df.rename(columns={'uuid': 'id', 'time': 'regdate'}, inplace=True)
        return df

    @staticmethod
    def validate_db_credentials(username, password, database, url, port):
        client = InfluxDBClient(host=url, port=port, username=username, password=password, database=database)

        try:
            client.query('SHOW DATABASES')
            return client

        except exceptions.InfluxDBClientError as e:
            raise Exception(f"Unable to create the InfluxDB client. {e}")
