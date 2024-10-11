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
) -> None:
    if len(extent) == 0:
        extent = get_frame_extent(route.full_route)
    if plot_background_map:
        background_map = create_background_map(extent)
    plot_route_on_map(route, False)
    if route.display_name is not None and route.display_name != "":
        plot_name_icon(route)
    if cfg["add_trail_to_movies"]:
        background_map.add_collection(get_trail(route))
    if add_data:
        add_data_to_bottom(
            extent,
            route.length[-1],
            route.altitude[-1],
            route.time[-1],
            np.nan_to_num(route.speed[-1]),
        )
    plt.axis("off")
    plt.tight_layout()
    if ffmpeg_writer is not None:
        ffmpeg_writer.grab_frame()
        plt.clf()


def plot_name_icon(route: Route) -> None:
    icon_size = 80 if len(route.display_name) <= 1 else 140
    plt.scatter(
        route.longitude[-1],
        route.latitude[-1],
        icon_size,
        zorder=9,
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
        zorder=10,
        horizontalalignment="center",
        verticalalignment="center_baseline",
    )


def get_dynamic_frame_extent_for_multiple_routes(
    subroutes: List[Route], min_size_in_deg: float = cfg["default_min_frame_size_in_deg"]
) -> List[float]:
    mean_point_between_routes = [0.0, 0.0]
    max_distance = min_size_in_deg
    for subroute in subroutes:
        mean_point_between_routes[0] += subroute.longitude[-1] / len(subroutes)
        mean_point_between_routes[1] += subroute.latitude[-1] / len(subroutes)
    for subroute in subroutes:
        distance_to_mean_point = np.sqrt(
            (mean_point_between_routes[0] - subroute.longitude[-1]) ** 2
            + (mean_point_between_routes[1] - subroute.latitude[-1]) ** 2
        )
        if distance_to_mean_point > max_distance:
            max_distance = distance_to_mean_point
    return [
        mean_point_between_routes[0]
        - 2 * max_distance * (1.0 + cfg["map_extent_adjust"]),
        mean_point_between_routes[0]
        + 2 * max_distance * (1.0 + cfg["map_extent_adjust"]),
        mean_point_between_routes[1] - max_distance * (1.0 + cfg["map_extent_adjust"]),
        mean_point_between_routes[1] + max_distance * (1.0 + cfg["map_extent_adjust"]),
    ]


def get_trail(route: Route) -> LineCollection:
    route_length = route.max_index
    alpha = np.zeros(route_length)
    trail_length = int(0.05 * route_length)
    if route.max_index > trail_length:
        alpha[route.max_index - trail_length : route.max_index] = np.arange(
            trail_length
        ).astype(float) / float(trail_length)
    else:
        alpha[0 : route.max_index] = np.arange(route.max_index).astype(float) / float(
            route.max_index
        )
    colorfade = colors.to_rgb(route.color) + (0.0,)
    cmap = colors.LinearSegmentedColormap.from_list("my", [colorfade, route.color])
    points = np.vstack((route.longitude, route.latitude)).T.reshape(-1, 1, 2)
    segments = np.hstack((points[:-1], points[1:]))
    lc = LineCollection(
        segments, lw=3, zorder=8, transform=ccrs.PlateCarree(), array=alpha, cmap=cmap
    )
    return lc
