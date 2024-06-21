import pandas as pd
from datetime import datetime
import pytz
import numpy as np

kst = pytz.timezone('Asia/Seoul')


class MakeDataFrame:
    def __init__(self):
        self.today_date = datetime.now(kst)

    @staticmethod
    def data_interpolation(df: pd.DataFrame) -> pd.DataFrame:
        df['resource_pct'] = df.groupby(
            ['id', 'resource_id']
        )['resource_pct'].transform(lambda x: x.interpolate(method='linear', limit_direction='both'))

        return df

    @staticmethod
    def cpu_percent_change(df: pd.DataFrame) -> pd.DataFrame:
        df.loc[
            df["resource_id"].str.contains("cpu"), "resource_pct"
        ] = df.loc[
            df["resource_id"].str.contains("cpu"), "resource_pct"
        ].apply(lambda x: 100 - x if not pd.isna(x) else np.nan)

        return df

    def preprocess_run(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self.cpu_percent_change(df=df)
        df = self.data_interpolation(df=df)
        return df
