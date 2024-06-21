import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from fastapi import FastAPI
from api import anomaly, health_check
import uvicorn

app = FastAPI(
    title="M-CMP Anomaly DOCS",
    description="M-CMP"
)

app.include_router(anomaly.router)
app.include_router(health_check.router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001)