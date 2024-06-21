import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from .system_controller import MakeDataFrame
from model.influxdb_connector import InfluxDBConn
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import pytz
import rrcf


kst = pytz.timezone('Asia/Seoul')


class AnomalyDetector:
    def __init__(self, id_connection_data: list):
        super(AnomalyDetector, self).__init__()
        self.id = id_connection_data.id
        self.num_trees = 10
        self.shingle_ratio = 0.01
        self.tree_size = 1024
        self.anomaly_threshold = 2.5

    @staticmethod
    def normalize_scores(scores):
        min_score = np.min(scores)
        max_score = np.max(scores)
        return (scores - min_score) / (max_score - min_score)

    @staticmethod
    def calculate_anomaly_threshold(complete_scores, anomaly_range_size):
        mean_score = np.mean(complete_scores)
        std_dev = np.std(complete_scores)
        return mean_score + anomaly_range_size * std_dev

    def run_RRCF(self, df, num_trees, shingle_size, tree_size, anomaly_range_size):
        forest = [rrcf.RCTree() for _ in range(num_trees)]

        data = df['resource_pct']
        shingled_data = rrcf.shingle(data, size=shingle_size)
        shingled_data = np.vstack([point for point in shingled_data])
        rrcf_scores = []

        for index, point in enumerate(shingled_data):
            for tree in forest:
                if len(tree.leaves) > tree_size:
                    tree.forget_point(index - tree_size)
                tree.insert_point(point, index=index)

            avg_codisp = np.mean([tree.codisp(index) for tree in forest])
            rrcf_scores.append(avg_codisp)

        normalized_scores = self.normalize_scores(np.array(rrcf_scores))

        initial_scores = np.full(shingle_size - 1, normalized_scores[0])
        complete_scores = np.concatenate([initial_scores, normalized_scores])
        anomaly_threshold = self.calculate_anomaly_threshold(complete_scores, anomaly_range_size)
        anomalies = complete_scores > anomaly_threshold
        results = pd.DataFrame({
            'anomaly_time': df['regdate'],
            'data_value': data,
            'anomaly_score': complete_scores,
            'anomaly_label': anomalies.astype(int)
        })

        return results, anomaly_threshold

    @staticmethod
    def complete_df(ori_df: pd.DataFrame, result_df: pd.DataFrame) -> pd.DataFrame:
        result_df = result_df[result_df['anomaly_label'] == 1]
        result_df['id'] = ori_df['id'].iloc[0]
        result_df['resource_id'] = ori_df['resource_id'].iloc[0]
        return result_df

    def calculate_anomaly_score(self, df: pd.DataFrame):
        shingle_size = int(len(df) * self.shingle_ratio)
        results, thr = self.run_RRCF(df=df, num_trees=self.num_trees, shingle_size=shingle_size
                                     , tree_size=self.tree_size, anomaly_range_size=self.anomaly_threshold)
        results = self.complete_df(ori_df=df, result_df=results)

        results = results[results['anomaly_label'] == 1]
        return results


class AnomalyProcessor:
    def __init__(self, id_connection_data: list):
        self.preprocess_data = None
        self.id_connection_data = id_connection_data[0]
        self.raw_data = None

    def get_raw_data(self):
        influxdb_client = InfluxDBConn(id_connection_data=self.id_connection_data)
        id = "'" + self.id_connection_data.id + "'"
        query_string = f'SELECT mean("usage_idle") as resource_pct ' \
                       f'FROM "{self.id_connection_data.database}"."{self.id_connection_data.retentionPolicy}"."cpu" ' \
                       f'WHERE time > now() - 1000m AND time < now() AND ("uuid" = {id}) GROUP BY "uuid", time(1m) FILL(null)'
        raw_data = influxdb_client.get_dataframe(query_string=query_string)
        self.raw_data = raw_data

    def set_timezone(self):
        self.raw_data['regdate'] = pd.to_datetime(self.raw_data['regdate'], utc=True)
        self.raw_data['regdate'] = self.raw_data['regdate'].dt.tz_localize(None) + timedelta(hours=9)

    def make_preprocess_data(self):
        preprocessor = MakeDataFrame()
        df = preprocessor.preprocess_run(df=self.raw_data)
        return df

    def add_data_info(self, df: pd.DataFrame):
        input_time = datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')
        df['regdate'] = input_time
        return df

    def run_anomaly_detection(self):
        self.get_raw_data()
        self.set_timezone()
        df = self.make_preprocess_data()

        anomaly_detector = AnomalyDetector(id_connection_data=self.id_connection_data)
        score_df = anomaly_detector.calculate_anomaly_score(df=df)
        score_df = self.add_data_info(score_df)

        return score_df
