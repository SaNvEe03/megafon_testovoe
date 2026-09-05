import math
import statistics
import time

import h3
import numpy as np
import simplekml

CENTER_LAT = 56.0
CENTER_LON = 38.0
RADIUS = 7.0


def create_massive(center_lat: float, center_lon: float, radius_km: float, resolution: int):
    center_cell = h3.latlng_to_cell(center_lat, center_lon, resolution)
    center = (center_lat, center_lon)
    edge_km = h3.average_hexagon_edge_length(resolution, unit='km')
    k = max(1, math.ceil(radius_km / edge_km))

    while True:
        ring = h3.grid_ring(center_cell, k)
        ring_dists = [h3.great_circle_distance(center, h3.cell_to_latlng(c), unit='km') for c in ring]
        if any(d < radius_km for d in ring_dists):
            k += 5
        else:
            break

    disk = h3.grid_disk(center_cell, k)

    result = []
    for cell in disk:
        dist = h3.great_circle_distance(center, h3.cell_to_latlng(cell), unit='km')
        if dist < radius_km:
            idx = h3.str_to_int(cell)
            level = (idx // 512) % 74 - 120
            cell_id = (idx // 512) % 100 + 1
            result.append([cell, level, cell_id])

    return result


def haversine_km(lat1, lon1, lat2, lon2):
    """Расстояние по большому кругу — та же формула, что использует h3.great_circle_distance."""
    R = 6371.008
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlmb = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlmb / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def data_in_hex(hex_id: str, dataset: list):
    current_res = h3.get_resolution(hex_id)
    child_hexagons = h3.cell_to_children(hex_id, current_res + 2)
    lookup = {row[0]: row for row in dataset}
    return [lookup[c] for c in child_hexagons if c in lookup]


def avg_func(res: int, dataset: list):
    groups = {}
    for cell, level, cell_id in dataset:
        parent = h3.cell_to_parent(cell, res)
        key = (parent, cell_id)
        groups.setdefault(key, []).append(level)

    avg_result = []
    for (parent, cell_id), levels in groups.items():
        median_level = math.floor(statistics.median(levels))
        avg_result.append([parent, median_level, cell_id])
    return avg_result


def point_in_polygon(lat: float, lon: float, polygon: list[tuple[float, float]]) -> bool:
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        lat_i, lon_i = polygon[i]
        lat_j, lon_j = polygon[j]
        if (lon_i > lon) != (lon_j > lon):
            lat_intersect = (lat_j - lat_i) * (lon - lon_i) / (lon_j - lon_i) + lat_i
            if lat < lat_intersect:
                inside = not inside
        j = i
    return inside


def parse_border(border: str) -> list[tuple[float, float]]:
    points = []
    for pair in border.split(','):
        lat_str, lon_str = pair.split('/')
        points.append((float(lat_str), float(lon_str)))
    return points


def bbox_func(border: str, dataset: list):
    polygon = parse_border(border)
    result = []
    for cell, level, cell_id in dataset:
        boundary = h3.cell_to_boundary(cell)
        if all(point_in_polygon(lat, lon, polygon) for lat, lon in boundary):
            result.append([cell, level, cell_id])
    return result


def build_kml(hexagons: list) -> str:
    kml = simplekml.Kml()
    for cell, level, cell_id in hexagons:
        coords = [(lon, lat) for lat, lon in h3.cell_to_boundary(cell)]
        coords.append(coords[0])  # замыкаем кольцо
        pol = kml.newpolygon(name=cell, outerboundaryis=coords)
        pol.description = f"level={level}, cell_id={cell_id}"
    return kml.kml()


def bbox_kml_func(border: str, dataset: list) -> str:
    hexagons = bbox_func(border, dataset)
    return build_kml(hexagons)
