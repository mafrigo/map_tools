import numpy as np
import matplotlib.pyplot as plt
from matplotlib import colors
from matplotlib.collections import LineCollection
import cartopy.crs as ccrs
from .route import Route, SubRoute
from .config import get_yaml_config
from .plotting import get_frame_extent, create_background_map, plot_route_on_map, add_data_to_bottom
from typing import List

cfg = get_yaml_config()


def plot_frame(route: Route | SubRoute, extent: List[float] = None):
    if extent is None:
        extent = get_frame_extent(route.full_route)
    background_map = create_background_map(extent)
    plot_route_on_map(route, False)
    add_data_to_bottom(extent,
                       "Total length: %3i km" % route.length[-1],
                       "Elevation: %4i m" % (route.altitude[-1]),
                       "Current speed: %2i km/h" % (np.nan_to_num(route.speed[-1])))
    if route.display_name is not None and route.display_name != "":
        plot_name_icon(route)
    if cfg["add_trail_to_movies"]:
        background_map.add_collection(get_trail(route))
    plt.axis('off')
    plt.tight_layout()


def plot_name_icon(route):
    plt.scatter(route.longitude[-1], route.latitude[-1], 150, zorder=9,
                transform=ccrs.PlateCarree(), facecolor='w', edgecolor=route.color)
    plt.text(route.longitude[-1], route.latitude[-1], route.display_name, color=cfg["text_color"], fontsize='x-small',
             transform=ccrs.PlateCarree(), zorder=10, horizontalalignment='center', verticalalignment='center_baseline')


def get_trail(route: Route | SubRoute) -> LineCollection:
    if isinstance(route, SubRoute):
        route_length = route.full_route.max_index
    else:
        route_length = route.max_index
    alpha = np.zeros(route_length)
    trail_length = int(0.05 * route_length)
    if route.max_index > trail_length:
        alpha[route.max_index - trail_length:route.max_index] = np.arange(trail_length).astype(float) / float(
            trail_length)
    else:
        alpha[0:route.max_index] = np.arange(route.max_index).astype(float) / float(route.max_index)
    colorfade = colors.to_rgb(route.color) + (0.0,)
    cmap = colors.LinearSegmentedColormap.from_list('my', [colorfade, route.color])
    points = np.vstack((route.longitude, route.latitude)).T.reshape(-1, 1, 2)
    segments = np.hstack((points[:-1], points[1:]))
    lc = LineCollection(segments, lw=3, zorder=8, transform=ccrs.PlateCarree(), array=alpha, cmap=cmap)
    return lc
