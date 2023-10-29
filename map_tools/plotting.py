import numpy as np
import matplotlib.pyplot as plt
from matplotlib import colors
from matplotlib.collections import LineCollection
import cartopy.crs as ccrs
import cartopy.io.img_tiles as cimgt
from .route_reader import SubRoute
from .config import get_yaml_config

cfg = get_yaml_config()


def get_zoom_level(delta):
    return int(np.clip(np.round(np.log2((cfg["osm_extra_zoom"] + 1.) * 360. / delta)), 0, 20))


def get_frame_extent(route, fixed_shape=True, fixed_size=0., center_on_last=False):
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
        if center_on_last:
            center = [route.longitude[-1], route.latitude[-1]]
        else:
            center = [np.min(route.longitude) + 0.5 * (np.max(route.longitude) - np.min(route.longitude)),
                      np.min(route.latitude) + 0.5 * (np.max(route.latitude) - np.min(route.latitude))]
        extent = [center[0] - 0.5 * deg_size * (1. + cfg["zoomout_fac"]),
                  center[0] + 0.5 * deg_size * (1. + cfg["zoomout_fac"]),
                  center[1] - 0.25 * deg_size * (1. + cfg["zoomout_fac"]),
                  center[1] + 0.25 * deg_size * (1. + cfg["zoomout_fac"])]
    return extent


def plot_route_on_map(route, extent=None, osm_request=None, output_file='map'):
    if isinstance(route, SubRoute):  # movie
        full_route = route.full_route
        add_trail_flag = True
        show_length = True
        show_current_stats = True
        show_total_stats = False
    else:  # single plot
        full_route = route
        add_trail_flag = False
        show_length = True
        show_current_stats = False
        show_total_stats = True

    total_length = route.length[-1]
    if extent is None:
        extent = get_frame_extent(full_route)
    else:
        route = route[np.logical_and(np.logical_and(route.longitude > extent[0], route.longitude < extent[1]),
                                     np.logical_and(route.latitude > extent[2], route.latitude < extent[3]))]
    deg_size = (extent[1] - extent[0]) / (1. + cfg["zoomout_fac"])

    # Plot background map
    if osm_request is None:
        osm_request = cimgt.OSM()
    ax = plt.axes(projection=osm_request.crs)
    ax.set_extent(extent)
    ax.add_image(osm_request, get_zoom_level(deg_size))

    # Plot route
    plt.plot(route.longitude, route.latitude, color=cfg["route_color"], transform=ccrs.PlateCarree(), lw=1)

    # Plot data
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
                 "Total elevation: %4i m" % (full_route.elevation_gain[-1]), color=cfg["route_color"],
                 transform=ccrs.PlateCarree(),
                 horizontalalignment='center')
        moving_speed = route.speed[route.speed > 10.]
        plt.text(extent[1] - 0.02 * (extent[1] - extent[0]), extent[2] - 0.05 * (extent[3] - extent[2]),
                 "Avg. speed: %2i km/h" % (np.mean(moving_speed)), color=cfg["route_color"],
                 transform=ccrs.PlateCarree(),
                 horizontalalignment='right')

    if add_trail_flag:
        add_trail(ax, route)

    plt.axis('off')
    plt.tight_layout()
    if output_file is not None:
        plt.savefig("output/" + output_file)


def add_trail(ax, route):
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
