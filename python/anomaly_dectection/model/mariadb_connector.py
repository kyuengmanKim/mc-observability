from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import pytz

kst = pytz.timezone('Asia/Seoul')


class MariaDBEngineConn:
    def __init__(self, username, password, database, ip):
        self.username = username
        self.password = password
        self.database = database
        self.ip = ip
        self.engine = self.create_engine()

    def create_engine(self):
        DB_URL = f"mysql+pymysql://{self.username}:{self.password}@{self.ip}:3306/{self.database}"
        engine = create_engine(DB_URL, pool_recycle=500)
        self.validate_db_credentials(engine)
        return engine

    @staticmethod
    def validate_db_credentials(engine):
        engine.connect()


    @contextmanager
    def session(self):
        if not self.engine:
            error_msg = "Engine not found. Please create the engine first."
            raise Exception(error_msg)
        session = None

        try:
            Session = sessionmaker(bind=self.engine)
            session = Session()
            yield session

        except Exception:
            if session:
                session.rollback()
            raise
        finally:
            if session:
                session.close()
                self.engine.dispose()