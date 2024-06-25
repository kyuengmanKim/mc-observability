from sqlalchemy import Column, Float, String, TIMESTAMP
from sqlalchemy.dialects.mysql import BIGINT, SMALLINT
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class AnomalyDetectionHistory(Base):
    __tablename__ = 'anomaly_detection'

    seq = Column(BIGINT(20), primary_key=True)
    id = Column(String(100), nullable=True)
    resource_id = Column(String(50), nullable=True)
    data_value = Column(Float(5), nullable=False)
    anomaly_score = Column(Float(5), nullable=False)
    anomaly_label = Column(SMALLINT(2), nullable=False)
    anomaly_time = Column(TIMESTAMP, nullable=False)
    regdate = Column(TIMESTAMP, nullable=False)