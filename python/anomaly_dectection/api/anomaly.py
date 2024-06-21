import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

import pytz
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from model.mariadb_connector import MariaDBEngineConn
from util.mariadb_utils import save_df_to_db
from model.mariadb_info import AnomalyDetectionHistory
from controller.anomaly_controller import AnomalyProcessor


class IDConnectionInfo(BaseModel):
    id: str
    url: str
    retentionPolicy: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None


class IDConnectionList(BaseModel):
    connections: List[IDConnectionInfo]


kst = pytz.timezone('Asia/Seoul')
router = APIRouter()


@router.post("/anomaly", tags=["anomaly"])
def anomaly_detector(id_connection_data: IDConnectionList):
    start_time = datetime.now(kst)
    processor = AnomalyProcessor(id_connection_data.connections)
    anomaly_score_df = processor.run_anomaly_detection()
    db_model = AnomalyDetectionHistory

    with MariaDBEngineConn(username='root', password='1234', database='mcmp_anomaly', ip='localhost').session() as db_session:
        save_df_to_db(df=anomaly_score_df, model_class=db_model, db_session=db_session)

    return_body = {
        "state": "Success",
        "total_running_time": str(datetime.now(kst) - start_time)
    }

    return JSONResponse(content=return_body)


@router.get("/anomaly", tags=["anomaly"])
def get_anomaly_result(id: Optional[str] = None):
    db_model = AnomalyDetectionHistory
    with MariaDBEngineConn(username='root', password='1234', database='mcmp_anomaly', ip='localhost').session() as db_session:
        if id:
            query = db_session.query(db_model).filter(db_model.id == id)
        else:
            query = db_session.query(db_model)
    anomaly_data = query.all()
    return anomaly_data

