import numpy as np
import matplotlib.pyplot as plt
from matplotlib import colors
from matplotlib.collections import LineCollection
import cartopy.crs as ccrs
import cartopy.io.img_tiles as img_tiles
from .route import Route, SubRoute
from .config import get_yaml_config
from typing import List

cfg = get_yaml_config()


def plot(route: Route | SubRoute, extent: List[int] = None, osm_request: img_tiles.OSM = None,
                      output_file: str = 'map', color_segments: bool = False):

    if extent is None:
        extent = get_frame_extent(route.full_route)
    else:
        route = route[np.logical_and(np.logical_and(route.longitude > extent[0], route.longitude < extent[1]),
                                     np.logical_and(route.latitude > extent[2], route.latitude < extent[3]))]
    deg_size = (extent[1] - extent[0]) / (1. + cfg["zoomout_fac"])

    ax = create_background_map(extent, deg_size, osm_request)

    plot_route_on_map(route, color_segments)

    if isinstance(route, SubRoute):  # used in movies, so show current stats instead of total ones
        add_data(route, extent, True, True, False)
        add_trail(ax, route)
    else:
        add_data(route, extent, True, False, True)

    plt.axis('off')
    plt.tight_layout()
    if output_file is not None:
        plt.savefig("output/" + output_file)


def get_zoom_level(delta: int):
    return int(np.clip(np.round(np.log2((cfg["osm_extra_zoom"] + 1.) * 360. / delta)), 0, 20))


def get_frame_extent(route: Route | SubRoute, fixed_shape: bool = True, fixed_size: float = 0.,
                     center_on: str = "frame"):
    if fixed_size == 0.:
        lat_route_diff = abs(np.max(route.latitude) - np.min(route.latitude))
        lon_route_diff = abs(np.max(route.longitude) - np.min(route.longitude))
        deg_size = np.max([2 * lat_route_diff, lon_route_diff])
    else:
        deg_size = fixed_size
    if not fixed_shape:
        extent = [np.min(route.longitude) - deg_size * cfg["zoomout_fac"],
                  np.max(route.longitude) + deg_size * cfg["zoomout_fac"],
                  np.min(route.latitude) - deg_size * cfg["zoomout_fac"],
                  np.max(route.latitude) + deg_size * cfg["zoomout_fac"]]
    else:
        if center_on == "frame":
            center = [np.min(route.longitude) + 0.5 * (np.max(route.longitude) - np.min(route.longitude)),
                      np.min(route.latitude) + 0.5 * (np.max(route.latitude) - np.min(route.latitude))]
        elif center_on == "last":
            center = [route.longitude[-1], route.latitude[-1]]
        elif center_on == "last_smooth":
            center = [np.mean(route.longitude[-5:-1]), np.mean(route.latitude[-5:-1])]
        else:
            raise IOError("Centering mode can only be last, frame, or last_smooth")
        extent = [center[0] - 0.5 * deg_size * (1. + cfg["zoomout_fac"]),
                  center[0] + 0.5 * deg_size * (1. + cfg["zoomout_fac"]),
                  center[1] - 0.25 * deg_size * (1. + cfg["zoomout_fac"]),
                  center[1] + 0.25 * deg_size * (1. + cfg["zoomout_fac"])]
    return extent


def create_background_map(extent: List[int], deg_size: int, osm_request: img_tiles.OSM = None) -> plt.Axes:
    if osm_request is None:
        osm_request = img_tiles.OSM(cache=True)
    ax = plt.axes(projection=osm_request.crs)
    ax.set_extent(extent)
    ax.add_image(osm_request, get_zoom_level(deg_size))
    return ax


def plot_route_on_map(route: Route | SubRoute, color_segments: bool = False):
    if color_segments:
        color_list = ["crimson", "g", "b"]
        route_colors = list(np.array(color_list)[route.route_segment_id.astype(int) % len(color_list)])
        plt.scatter(route.longitude, route.latitude, color=route_colors, transform=ccrs.PlateCarree(), lw=1, s=1, marker='.')
    else:
        plt.plot(route.longitude, route.latitude, color=cfg["route_color"], transform=ccrs.PlateCarree(), lw=1)


def add_data(route: Route | SubRoute, extent: List[int], show_length: bool, show_current_stats: bool, show_total_stats: bool):
    total_length = route.length[-1]
    if show_length:
        plt.text(extent[0] + 0.02 * (extent[1] - extent[0]), extent[2] - 0.05 * (extent[3] - extent[2]),
                 "Total length: %3i km" % total_length, color=cfg["route_color"], transform=ccrs.PlateCarree(),
                 horizontalalignment='left')
    if show_current_stats:
        plt.text(extent[0] + 0.5 * (extent[1] - extent[0]), extent[2] - 0.05 * (extent[3] - extent[2]),
                 "Elevation: %4i m" % (route.altitude[-1]), color=cfg["route_color"], transform=ccrs.PlateCarree(),
                 horizontalalignment='center')
        plt.text(extent[1] - 0.02 * (extent[1] - extent[0]), extent[2] - 0.05 * (extent[3] - extent[2]),
                 "Current speed: %2i km/h" % (np.nan_to_num(route.speed[-1])), color=cfg["route_color"],
                 transform=ccrs.PlateCarree(),
                 horizontalalignment='right')
    if show_total_stats:
        plt.text(extent[0] + 0.5 * (extent[1] - extent[0]), extent[2] - 0.05 * (extent[3] - extent[2]),
                 "Total elevation: %4i m" % (route.full_route.elevation_gain[-1]), color=cfg["route_color"],
                 transform=ccrs.PlateCarree(),
                 horizontalalignment='center')
        moving_speed = route.speed[route.speed > 10.]
        plt.text(extent[1] - 0.02 * (extent[1] - extent[0]), extent[2] - 0.05 * (extent[3] - extent[2]),
                 "Avg. speed: %2i km/h" % (np.mean(moving_speed)), color=cfg["route_color"],
                 transform=ccrs.PlateCarree(),
                 horizontalalignment='right')

def add_trail(ax: plt.Axes, route: Route | SubRoute):
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
    colorfade = colors.to_rgb(cfg["route_color"]) + (0.0,)
    cmap = colors.LinearSegmentedColormap.from_list('my', [colorfade, cfg["route_color"]])
    points = np.vstack((route.longitude, route.latitude)).T.reshape(-1, 1, 2)
    segments = np.hstack((points[:-1], points[1:]))
    lc = LineCollection(segments, lw=3, zorder=10, transform=ccrs.PlateCarree(), array=alpha, cmap=cmap)
    ax.add_collection(lc)
