from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, Response
from pydantic import BaseModel

from .first import (
    avg_func,
    bbox_func,
    bbox_kml_func,
    create_massive,
    data_in_hex,
)

CENTER_LAT = 56.0
CENTER_LON = 38.0
RADIUS = 7.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    global dataset
    dataset = create_massive(
        center_lat=CENTER_LAT,
        center_lon=CENTER_LON,
        radius_km=RADIUS,
        resolution=12,
    )
    yield


app = FastAPI(lifespan=lifespan)


class Hex_schema(BaseModel):
    hex_index: str


class AVG_chema(BaseModel):
    resolution: int


@app.get("/hex")
async def get_hex_index(hex: str | None = Query(default=None)):
    result = data_in_hex(hex, dataset)
    return result


@app.get("/avg")
async def avg(avg: AVG_chema = Query(default=None)):
    result = avg_func(avg.resolution, dataset)
    return result


@app.get("/bbox")
async def get_bbox(border: str = Query(...)):
    result = bbox_func(border, dataset)
    return result


@app.get("/bbox_kml")
async def get_bbox_kml(border: str = Query(...)):
    kml_content = bbox_kml_func(border, dataset)
    return Response(
        content=kml_content,
        media_type="application/vnd.google-earth.kml+xml",
        headers={"Content-Disposition": "attachment; filename=bbox.kml"},
    )
