import pandas as pd
from sqlalchemy.exc import PendingRollbackError
import pytz

kst = pytz.timezone('Asia/Seoul')


def data_save_process(db_session, data, recur_init=False, delete_logic=False, add_logic=False):
    try:
        if delete_logic:
            db_session.delete(data)
        elif add_logic:
            db_session.add(data)
        else:
            db_session.add_all(data)
        db_session.commit()
    except PendingRollbackError as pe_msg:
        db_session.rollback()
        if recur_init:
            raise pe_msg
        else:
            data_save_process(db_session=db_session, data=data, recur_init=True)

    return


def save_df_to_db(df, model_class, db_session):
    objs = []
    for _, row in df.iterrows():
        row = row.where(pd.notnull(row), None)
        obj = model_class(**row.to_dict())
        objs.append(obj)

    data_save_process(db_session=db_session, data=objs)
    return