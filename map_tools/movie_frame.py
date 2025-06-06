import numpy as np
import matplotlib.pyplot as plt
from matplotlib import colors
from matplotlib.collections import LineCollection
import cartopy.crs as ccrs
from .route import Route
from .config import get_yaml_config
from .plotting import (
    get_frame_extent,
    create_background_map,
    plot_route_on_map,
    add_data_to_bottom,
)
from typing import List
import matplotlib.animation as mani

cfg = get_yaml_config()


def plot_frame(
        route: Route,
        ffmpeg_writer: mani.FFMpegWriter,
        extent: List[float] = list(),
        plot_background_map: bool = True,
        add_data: bool = True,
        speed_moving_window: int = 4 * cfg["frames_per_second"],
        include_trail: bool = True,
        zorder_modifier: int = 0,
        show_avg_speed: bool = False,
) -> None:
    if len(extent) == 0:
        extent = get_frame_extent(route.full_route)
    if plot_background_map:
        background_map = create_background_map(extent)
    plot_route_on_map(route, False)
    if route.display_name is not None and route.display_name != "":
        plot_name_icon(route, zorder_modifier)
    if cfg["add_trail_to_movies"] and include_trail:
        plt.gca().add_collection(get_trail(route))
    if add_data:
        if route.max_index > 1:
            if not show_avg_speed:
                speed = np.round(np.mean(route.speed[np.max([route.max_index - speed_moving_window, 0]):-1]))
            else:
                speed = np.mean(route.speed[route.speed > cfg["minimum_moving_speed"]])
        else:
            speed = 0
        add_data_to_bottom(
            extent,
            route.length[-1],
            route.altitude[-1],
            route.time[-1],
            speed,
        )
    plt.axis("off")
    plt.tight_layout()
    if ffmpeg_writer is not None:
        ffmpeg_writer.grab_frame()
        plt.clf()


def plot_name_icon(route: Route, zorder_modifier: int = 0) -> None:
    icon_size = 80 if len(route.display_name) <= 1 else 140
    plt.scatter(
        route.longitude[-1],
        route.latitude[-1],
        icon_size,
        zorder=9 + zorder_modifier,
        transform=ccrs.PlateCarree(),
        facecolor="w",
        edgecolor=route.color,
    )
    plt.text(
        route.longitude[-1],
        route.latitude[-1],
        route.display_name,
        color=cfg["text_color"],
        fontsize="x-small",
        transform=ccrs.PlateCarree(),
        zorder=10 + zorder_modifier,
        horizontalalignment="center",
        verticalalignment="center_baseline",
    )


def get_dynamic_frame_extent_for_multiple_routes(
        subroutes: List[Route], min_size_in_deg: float = cfg["default_min_frame_size_in_deg"]) -> List[float]:
    mean_point_between_routes = [0.0, 0.0]
    max_distance = min_size_in_deg
    smoothing_window = np.min([cfg["frames_per_second"], np.min([sr.max_index for sr in subroutes])])
    for subroute in subroutes:
        mean_point_between_routes[0] += np.mean(subroute.longitude[-smoothing_window:]) / len(subroutes)
        mean_point_between_routes[1] += np.mean(subroute.latitude[-smoothing_window:]) / len(subroutes)
    for subroute in subroutes:
        distance_to_mean_point = np.sqrt(
            (mean_point_between_routes[0] - subroute.longitude[-1]) ** 2
            + (mean_point_between_routes[1] - subroute.latitude[-1]) ** 2
        )
        if distance_to_mean_point > max_distance:
            max_distance = distance_to_mean_point
    map_horizontal_size = 2 * max_distance * (1.0 + cfg["map_extent_adjust"])
    map_vertical_size = max_distance * (1.0 + cfg["map_extent_adjust"])
    return [
        mean_point_between_routes[0] - map_horizontal_size,
        mean_point_between_routes[0] + map_horizontal_size,
        mean_point_between_routes[1] - map_vertical_size,
        mean_point_between_routes[1] + map_vertical_size,
    ]


def get_trail(route: Route, trail_width: int = 2) -> LineCollection:
    trail_length = 2 * cfg["frames_per_second"]
    alpha = np.arange(np.min([trail_length, route.max_index]))
    colorfade = colors.to_rgb(route.color) + (0.0,)
    cmap = colors.LinearSegmentedColormap.from_list("my", [colorfade, route.color])
    points = np.vstack((route.longitude[-trail_length:-1], route.latitude[-trail_length:-1])).T.reshape(-1, 1, 2)
    segments = np.hstack((points[:-1], points[1:]))
    lc = LineCollection(segments, lw=trail_width, zorder=8, transform=ccrs.PlateCarree(), array=alpha, cmap=cmap)
    return lc
