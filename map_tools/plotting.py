import math
import threading
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from typing import List

import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.io.img_tiles as img_tiles
from shapely import geometry as sgeom
from .route import Route
from .config import get_yaml_config

cfg = get_yaml_config()

_osm_tiles = None
_background_cache = OrderedDict()


class CachedOSM(img_tiles.OSM):
    """OSM tile source with an in-memory LRU cache on top of the disk cache.

    Without this, cartopy re-reads and re-decodes every tile from disk on
    every frame, even when the tile is fully cached.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._memory_cache = OrderedDict()
        self._cache_lock = threading.Lock()

    def is_cached(self, tile: tuple) -> bool:
        return tile in self._memory_cache

    def get_image(self, tile):
        if tile in self._memory_cache:
            with self._cache_lock:
                self._memory_cache.move_to_end(tile)
            return self._memory_cache[tile]
        image = super().get_image(tile)
        with self._cache_lock:
            self._memory_cache[tile] = image
            while len(self._memory_cache) > cfg.get("max_cached_tiles", 1000):
                self._memory_cache.popitem(last=False)
        return image


def get_osm_tiles() -> CachedOSM:
    global _osm_tiles
    if _osm_tiles is None:
        _osm_tiles = CachedOSM(cache=True)
    return _osm_tiles


def lonlat_to_tile_numbers(lon: float, lat: float, zoom: int) -> (float, float):
    # standard slippy map tile numbering, y = 0 at the north pole
    n_tiles = float(2 ** zoom)
    x = (lon + 180.0) / 360.0 * n_tiles
    lat_rad = math.radians(lat)
    y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n_tiles
    return x, y


def tile_number_y_to_lat(y: float, zoom: int) -> float:
    n_tiles = float(2 ** zoom)
    return math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * y / n_tiles))))


def prefetch_tiles(extents: List[List[float]]) -> None:
    """Download all OSM tiles required for the given extents up front, in parallel.

    This removes network latency from the render loop: afterwards every tile
    request hits the in-memory cache.
    """
    osm = get_osm_tiles()
    tiles = set()
    for extent in extents:
        deg_size = (extent[1] - extent[0]) / (1.0 + cfg["map_extent_adjust"])
        zoom = get_zoom_level(deg_size)
        x_min, y_top = lonlat_to_tile_numbers(extent[0], extent[3], zoom)
        x_max, y_bottom = lonlat_to_tile_numbers(extent[1], extent[2], zoom)
        for x in range(int(math.floor(x_min)), int(math.ceil(x_max))):
            for y in range(int(math.floor(y_top)), int(math.ceil(y_bottom))):
                tiles.add((x, y, zoom))
    missing = sorted(tile for tile in tiles if not osm.is_cached(tile))
    if len(missing) > 0:
        def fetch_tile(tile):
            try:
                osm.get_image(tile)
            except OSError:
                pass

        with ThreadPoolExecutor(max_workers=cfg.get("tile_prefetch_workers", 12)) as executor:
            list(executor.map(fetch_tile, missing))


def plot_single_route(
        route: Route,
        extent: List[float] = [],
        color_segments: bool = False,
        output_file: str = "map",
) -> None:
    if len(extent) == 0:
        extent = get_frame_extent(route.full_route)
    create_background_map(extent)
    plot_route_on_map(route, color_segments)
    moving_filter = route.speed > cfg["minimum_moving_speed"]
    if len(route.speed[moving_filter]) > 0:
        avg_speed = np.mean(route.speed[moving_filter])
        moving_time = np.sum(route.time_intervals[moving_filter])
    else:
        avg_speed = 0
        moving_time = 0
    add_data_to_bottom(
        extent,
        route.length[-1],
        route.elevation_gain[-1],
        moving_time,
        avg_speed,
    )
    plt.axis("off")
    plt.tight_layout()
    if output_file != "":
        plt.savefig("output/" + output_file, dpi=cfg["image_dpi_resolution"])
    plt.clf()


def plot_multiple_routes(
        routes: List[Route], extent: List[float] = [], output_file: str = "multi_map"
) -> None:
    if len(extent) == 0:
        extent = get_frame_extent_multiple(routes)
    create_background_map(extent)
    total_length = 0
    total_elevation = 0
    total_time = 0
    avg_speed = 0.
    for route in routes:
        plot_route_on_map(route, False)
        total_length += route.length[-1]
        total_elevation += route.elevation_gain[-1]
        total_time += route.time[-1]
        avg_speed += route.length[-1] * np.nan_to_num(np.mean(route.speed[route.speed > cfg["minimum_moving_speed"]]))
    add_data_to_bottom(
        extent,
        total_length,
        total_elevation,
        total_time,
        avg_speed / total_length,
    )
    plt.axis("off")
    plt.tight_layout()
    plt.savefig("output/" + output_file, dpi=cfg["image_dpi_resolution"])
    plt.clf()


def get_zoom_level(delta: float) -> int:
    return int(
        np.clip(
            np.round(np.log2((cfg["osm_zoom_level_adjust"] + 1.0) * 360.0 / delta)),
            0,
            20,
        )
    )


def get_frame_extent(
        route: Route,
        fixed_shape: bool = True,
        fixed_size: float = 0.0,
        center_on: str = "frame",
) -> List[float]:
    if fixed_size == 0.0:
        lat_route_diff = abs(np.max(route.latitude) - np.min(route.latitude))
        lon_route_diff = abs(np.max(route.longitude) - np.min(route.longitude))
        deg_size = np.max([2 * lat_route_diff, lon_route_diff])
    else:
        deg_size = fixed_size
    if not fixed_shape:
        extent = [
            np.min(route.longitude) - deg_size * cfg["map_extent_adjust"],
            np.max(route.longitude) + deg_size * cfg["map_extent_adjust"],
            np.min(route.latitude) - deg_size * cfg["map_extent_adjust"],
            np.max(route.latitude) + deg_size * cfg["map_extent_adjust"],
        ]
    else:
        if center_on == "frame":
            center = [
                np.min(route.longitude) + 0.5 * (np.max(route.longitude) - np.min(route.longitude)),
                np.min(route.latitude) + 0.5 * (np.max(route.latitude) - np.min(route.latitude)),
            ]
        elif center_on == "last":
            center = [route.longitude[-1], route.latitude[-1]]
        elif center_on == "last_smooth":
            smoothing_nframes = np.min([cfg["frames_per_second"], route.max_index])
            center = [np.mean(route.longitude[-smoothing_nframes:-1]),
                      np.mean(route.latitude[-smoothing_nframes:-1])]
        else:
            raise IOError("Centering mode can only be last, frame, or last_smooth")
        extent = [
            center[0] - 0.5 * deg_size * (1.0 + cfg["map_extent_adjust"]),
            center[0] + 0.5 * deg_size * (1.0 + cfg["map_extent_adjust"]),
            center[1] - 0.25 * deg_size * (1.0 + cfg["map_extent_adjust"]),
            center[1] + 0.25 * deg_size * (1.0 + cfg["map_extent_adjust"]),
        ]
    return extent


def get_frame_extent_multiple(routes: List[Route], fixed_shape: bool = True) -> List[float]:
    extent = [1000.0, -1000.0, 1000.0, -1000.0]
    for route in routes:
        current_extent = get_frame_extent(route, center_on="frame")
        if current_extent[0] < extent[0]:
            extent[0] = current_extent[0]
        if current_extent[2] < extent[2]:
            extent[2] = current_extent[2]
        if current_extent[1] > extent[1]:
            extent[1] = current_extent[1]
        if current_extent[3] > extent[3]:
            extent[3] = current_extent[3]
    if fixed_shape:
        horizontal_size = extent[1] - extent[0]
        vertical_size = extent[3] - extent[2]
        center_x = extent[0] + horizontal_size/2.
        center_y = extent[2] + vertical_size/2.
        if horizontal_size < 2 * vertical_size:
            new_horizontal_size = vertical_size * 2
            extent[0] = center_x - 0.5 * new_horizontal_size
            extent[1] = center_x + 0.5 * new_horizontal_size
        else:
            new_vertical_size = horizontal_size * 0.5
            extent[2] = center_y - 0.5 * new_vertical_size
            extent[3] = center_y + 0.5 * new_vertical_size
    return extent


def _fetch_stitched_tiles(osm: CachedOSM, tile_range: tuple) -> (np.ndarray, List[float]):
    zoom, x_min, x_max, y_min, y_max = tile_range
    n_tiles = float(2 ** zoom)
    lon_min = x_min / n_tiles * 360.0 - 180.0
    lon_max = x_max / n_tiles * 360.0 - 180.0
    lat_max = tile_number_y_to_lat(y_min, zoom)
    lat_min = tile_number_y_to_lat(y_max, zoom)
    tile_box = osm.crs.project_geometry(
        sgeom.box(lon_min, lat_min, lon_max, lat_max), ccrs.PlateCarree()
    )
    image, image_extent, _ = osm.image_for_domain(tile_box, zoom)
    return image, image_extent


def create_background_map(extent: List[float]) -> plt.Axes:
    osm = get_osm_tiles()
    deg_size = (extent[1] - extent[0]) / (1.0 + cfg["map_extent_adjust"])
    zoom = get_zoom_level(deg_size)
    x_min, y_top = lonlat_to_tile_numbers(extent[0], extent[3], zoom)
    x_max, y_bottom = lonlat_to_tile_numbers(extent[1], extent[2], zoom)
    tile_range = (
        zoom,
        int(math.floor(x_min)), int(math.ceil(x_max)),
        int(math.floor(y_top)), int(math.ceil(y_bottom)),
    )
    background = _background_cache.get(tile_range)
    if background is not None:
        _background_cache.move_to_end(tile_range)
    else:
        background = _fetch_stitched_tiles(osm, tile_range)
        _background_cache[tile_range] = background
        while len(_background_cache) > cfg.get("max_cached_background_maps", 200):
            _background_cache.popitem(last=False)
    image, image_extent = background
    ax = plt.axes(projection=osm.crs)
    ax.set_extent(extent)
    ax.imshow(image, extent=image_extent, origin="lower", transform=osm.crs)
    return ax


def plot_route_on_map(route: Route, color_segments: bool = False, cut_extent: List[float] = None) -> None:
    if cut_extent is not None:
        # route.length is monotonically increasing, so the points dropped by
        # the cut form a prefix that can be found with a binary search
        cutoff = route.length[-1] - (cut_extent[1] - cut_extent[0])
        first_dropped_index = int(np.searchsorted(route.length, cutoff, side="left"))
        if first_dropped_index > 0:
            route = route[:first_dropped_index]

    if color_segments:
        color_list = ["crimson", "g", "b"]
        route_colors = list(
            np.array(color_list)[route.route_segment_id.astype(int) % len(color_list)]
        )
        plt.scatter(
            route.longitude,
            route.latitude,
            color=route_colors,
            transform=ccrs.PlateCarree(),
            lw=cfg["route_thickness"],
            s=cfg["route_thickness"],
            marker=".",
        )
    else:
        plt.plot(
            route.longitude,
            route.latitude,
            color=route.color,
            transform=ccrs.PlateCarree(),
            lw=cfg["route_thickness"],
        )


def add_data_to_bottom(extent: List[float], distance: float, elevation_gain: float, time: float, speed: float) -> None:
    plt.text(
        extent[0] + 0.1 * (extent[1] - extent[0]),
        extent[2] - 0.05 * (extent[3] - extent[2]),
        "Distance",
        color=cfg["text_color"],
        transform=ccrs.PlateCarree(),
        horizontalalignment="center",
        fontsize=cfg["fontsize_small"],
    )
    plt.text(
        extent[0] + 0.1 * (extent[1] - extent[0]),
        extent[2] - 0.1 * (extent[3] - extent[2]),
        "%3i km" %distance,
        color=cfg["text_color"],
        transform=ccrs.PlateCarree(),
        horizontalalignment="center",
        weight="bold",
        fontsize=cfg["fontsize_large"],
    )
    plt.text(
        extent[0] + 0.35 * (extent[1] - extent[0]),
        extent[2] - 0.05 * (extent[3] - extent[2]),
        "Elevation",
        color=cfg["text_color"],
        transform=ccrs.PlateCarree(),
        horizontalalignment="center",
        fontsize=cfg["fontsize_small"],
    )
    plt.text(
        extent[0] + 0.35 * (extent[1] - extent[0]),
        extent[2] - 0.1 * (extent[3] - extent[2]),
        "%3i m" %elevation_gain,
        color=cfg["text_color"],
        transform=ccrs.PlateCarree(),
        horizontalalignment="center",
        weight="bold",
        fontsize=cfg["fontsize_large"],
    )
    plt.text(
        extent[0] + 0.65 * (extent[1] - extent[0]),
        extent[2] - 0.05 * (extent[3] - extent[2]),
        "Time",
        color=cfg["text_color"],
        transform=ccrs.PlateCarree(),
        horizontalalignment="center",
        fontsize=cfg["fontsize_small"],
    )
    hours = int(time/3600.)
    minutes = int((time-3600*hours)/60)
    plt.text(
        extent[0] + 0.65 * (extent[1] - extent[0]),
        extent[2] - 0.1 * (extent[3] - extent[2]),
        "%ih%im" %(hours, minutes),
        color=cfg["text_color"],
        transform=ccrs.PlateCarree(),
        horizontalalignment="center",
        weight="bold",
        fontsize=cfg["fontsize_large"],
    )
    plt.text(
        extent[1] - 0.1 * (extent[1] - extent[0]),
        extent[2] - 0.05 * (extent[3] - extent[2]),
        "Speed",
        color=cfg["text_color"],
        transform=ccrs.PlateCarree(),
        horizontalalignment="center",
        fontsize=cfg["fontsize_small"],
    )
    plt.text(
        extent[1] - 0.1 * (extent[1] - extent[0]),
        extent[2] - 0.1 * (extent[3] - extent[2]),
        "%.1f km/h" %np.round(speed, 1),
        color=cfg["text_color"],
        transform=ccrs.PlateCarree(),
        horizontalalignment="center",
        weight="bold",
        fontsize=cfg["fontsize_large"],
    )
