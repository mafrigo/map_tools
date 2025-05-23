import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.io.img_tiles as img_tiles
from .route import Route
from .config import get_yaml_config
from typing import List

cfg = get_yaml_config()


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
    add_data_to_bottom(
        extent,
        route.length[-1],
        route.elevation_gain[-1],
        np.nan_to_num(np.sum(route.time_intervals[route.speed > cfg["minimum_moving_speed"]])),
        np.nan_to_num(np.mean(route.speed[route.speed > cfg["minimum_moving_speed"]])),
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
                np.min(route.longitude)
                + 0.5 * (np.max(route.longitude) - np.min(route.longitude)),
                np.min(route.latitude)
                + 0.5 * (np.max(route.latitude) - np.min(route.latitude)),
            ]
        elif center_on == "last":
            center = [route.longitude[-1], route.latitude[-1]]
        elif center_on == "last_smooth":
            center = [np.mean(route.longitude[-5:-1]), np.mean(route.latitude[-5:-1])]
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
        current_extent = get_frame_extent(route)
        if current_extent[0] < extent[0]:
            extent[0] = current_extent[0]
        if current_extent[2] < extent[2]:
            extent[2] = current_extent[2]
        if current_extent[1] > extent[1]:
            extent[1] = current_extent[1]
        if current_extent[3] > extent[3]:
            extent[3] = current_extent[3]
    if fixed_shape:
        center_x = extent[0] + (extent[1] - extent[0])/2.
        center_y = extent[2] + (extent[3] - extent[2])/2.
        if extent[3] - extent[2] > 0.5 * (extent[1] - extent[0]):
            extent[0] = center_x - 0.5 * (extent[3] - extent[2])
            extent[1] = center_x + 0.5 * (extent[3] - extent[2])
        else:
            extent[2] = center_y - 0.25 * (extent[1] - extent[0])
            extent[3] = center_y + 0.25 * (extent[1] - extent[0])
        print(extent)
    return extent


def create_background_map(extent: List[float]) -> plt.Axes:
    deg_size = (extent[1] - extent[0]) / (1.0 + cfg["map_extent_adjust"])
    osm_request = img_tiles.OSM(cache=True)
    ax = plt.axes(projection=osm_request.crs)
    ax.set_extent(extent)
    ax.add_image(osm_request, get_zoom_level(deg_size))
    return ax


def plot_route_on_map(route: Route, color_segments: bool = False) -> None:
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
