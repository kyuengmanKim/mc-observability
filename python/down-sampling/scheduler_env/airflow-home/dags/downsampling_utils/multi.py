from influxdb import InfluxDBClient
import warnings
import pandas as pd
import numpy as np
from downsampling_utils.downsampling import weighted_moving_average, data_reduction
from urllib.parse import urlparse
import ast
from functools import reduce

warnings.filterwarnings('ignore', category=FutureWarning)


class DataProcessor:
    def __init__(self, output_db: dict, input_db: pd.DataFrame, start: str, end: str):
        self.start = start
        self.end = end
        self.host, self.port = self.parse_url(output_db['url'])
        self.username = output_db['username']
        self.password = output_db['password']
        self.database = output_db['database']

        self.save_client = InfluxDBClient(
            host=self.host, port=self.port,
            username=self.username, password=self.password,
            database=self.database
        )

        self.connection_df = input_db
        self.connection_df['MEASUREMENTS'] = self.connection_df['MEASUREMENTS'].apply(
            lambda x: ast.literal_eval(x) if isinstance(x, str) else x
        )

        self.measurements = list(set(sum(self.connection_df['MEASUREMENTS'], [])))
        self.connection_df[['host', 'port']] = self.connection_df['URL'].apply(
            lambda x: pd.Series(self.parse_url(x), index=['host', 'port'])
        )

    @staticmethod
    def parse_url(url):
        parsed_url = urlparse(url)
        return parsed_url.hostname, parsed_url.port

    def process_measurements(self):
        for measurement in self.measurements:
            clients, original_dataframes, all_tags, all_fields = self.init_measurement_processing(measurement)

            all_empty = all(df.empty for df in original_dataframes)
            if all_empty:
                print(f"No data exists in '{measurement}'.")
                continue

            merged_df = self.merge_dataframes(original_dataframes)
            all_tags_filtered = self.filter_existing_fields(merged_df, list(all_tags))
            all_fields_filtered = self.filter_existing_fields(merged_df, list(all_fields))

            result_df = self.downsample_and_reduce(merged_df, all_tags_filtered, all_fields_filtered)
            self.save_to_influx(measurement, result_df, all_tags_filtered, all_fields_filtered)
            print(f"{measurement} is saved.")

    def init_measurement_processing(self, measurement):
        clients = []
        original_dataframes = []
        all_tags = set()
        all_fields = set()

        for _, row in self.connection_df.iterrows():
            client = InfluxDBClient(
                host=row['host'], port=8086,
                username=row['USERNAME'], password=row['PASSWORD'],
                database=row['DATABASE']
            )
            clients.append(client)

            query = f'SELECT * FROM "{row["DATABASE"]}"."autogen"."{measurement}" WHERE time > \'{self.start}\' and time <= \'{self.end}\''
            print(query)
            result = client.query(query)
            original_data = pd.DataFrame(list(result.get_points()))
            if original_data.empty:
                continue
            original_dataframes.append(original_data)

            tags = self.get_keys_from_influx(client, measurement, "TAG")
            fields = self.get_keys_from_influx(client, measurement, "FIELD")

            all_tags.update(tags)
            all_fields.update(fields)

        return clients, original_dataframes, all_tags, all_fields

    @staticmethod
    def get_keys_from_influx(client, measurement, key_type):
        query = f'SHOW {key_type} KEYS FROM "{measurement}"'
        result_set = client.query(query)
        return {entry[f'{key_type.lower()}Key'] for entry in result_set.get_points()}

    @staticmethod
    def merge_dataframes(dataframes):
        common_columns = list(reduce(lambda x, y: x.intersection(y.columns), dataframes, set(dataframes[0].columns)))
        merged_df = dataframes[0]
        for df in dataframes[1:]:
            merged_df = pd.merge(merged_df, df, on=common_columns, how='outer')
        return merged_df.fillna(value=np.nan).infer_objects(copy=False)

    @staticmethod
    def filter_existing_fields(df, cols):
        return [col for col in cols if col in df.columns]

    def downsample_and_reduce(self, merged_df, all_tags_filtered, all_fields_filtered):
        merged_group_df = merged_df.groupby(all_tags_filtered, dropna=False)
        result_df = pd.DataFrame()

        for _, group_df in merged_group_df:
            wma_df = weighted_moving_average(group_df, all_fields_filtered)
            reduced_df = data_reduction(wma_df, all_fields_filtered, cut_size=10)
            for tag in all_tags_filtered:
                reduced_df[tag] = group_df[tag].iloc[0]
            result_df = pd.concat([result_df, reduced_df], ignore_index=True)

        return result_df

    def save_to_influx(self, measurement, result_df, tags, fields):
        try:
            data_points = self.df_to_influx_points(result_df, measurement, tags, fields)
            self.save_client.write_points(data_points)
        except Exception as msg:
            print('DB ERROR')
            print(msg)

    @staticmethod
    def df_to_influx_points(df, measurement_name, tags, fields):
        points = []
        for _, row in df.iterrows():
            point = {
                "measurement": measurement_name,
                "time": row['time'],
                "tags": {},
                "fields": {}
            }
            for col in df.columns:
                if col in tags:
                    if pd.notna(row[col]):
                        point['tags'][col] = str(row[col])
                elif col in fields:
                    if pd.notna(row[col]):
                        if isinstance(row[col], (int, float)):
                            point['fields'][col] = row[col]
                        else:
                            point['fields'][col] = str(row[col])

            points.append(point)
        return points
