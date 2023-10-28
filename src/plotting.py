import numpy as np
import matplotlib.pyplot as plt
from matplotlib import colors
from matplotlib.collections import LineCollection
import cartopy.crs as ccrs
import cartopy.io.img_tiles as cimgt
from .route_reader import SubRoute


def get_zoom_level(delta, extra_zoom=1.2):
    return int(np.clip(np.round(np.log2((extra_zoom+1.)*360./delta)), 0, 20))


def plot_route_on_map(route, zoomout_fac=0.4, route_color='r', extent=None,
                      osm_request=None, output_file='map'):
    if isinstance(route, SubRoute):  # movie
        full_route = route.full_route
        add_trail_flag = True
        show_length = True
        show_current_elevation = True
        show_total_elevation = False
        show_current_speed = True
        show_avg_speed = False
    else:  # single plot
        full_route = route
        add_trail_flag = False
        show_length = True
        show_current_elevation = False
        show_total_elevation = True
        show_current_speed = False
        show_avg_speed = True
    if extent is None:
        lat_route_diff = abs(np.max(full_route.latitude) - np.min(full_route.latitude))
        lon_route_diff = abs(np.max(full_route.longitude) - np.min(full_route.longitude))
        lon_size = np.max([2*lat_route_diff, lon_route_diff])
        extent = [np.min(full_route.longitude) - lon_size * zoomout_fac,
                  np.max(full_route.longitude) + lon_size * zoomout_fac,
                  np.min(full_route.latitude) - lon_size * zoomout_fac,
                  np.max(full_route.latitude) + lon_size * zoomout_fac]
    else:
        lon_size = (extent[1] - extent[0])/(1.+zoomout_fac)
        route = route[np.logical_and(np.logical_and(route.longitude > extent[0], route.longitude < extent[1]),
                                     np.logical_and(route.latitude > extent[2], route.latitude < extent[3]))]

    # Plot background map
    if osm_request is None:
        osm_request = cimgt.OSM()
    ax = plt.axes(projection=osm_request.crs)
    ax.set_extent(extent)
    ax.add_image(osm_request, get_zoom_level(lon_size))

    # Plot route
    plt.plot(route.longitude, route.latitude, color=route_color, transform=ccrs.PlateCarree(), lw=1)
    if show_length:
        plt.text(extent[0] + 0.02 * (extent[1] - extent[0]), extent[2] - 0.05 * (extent[3] - extent[2]),
                 "Total length: %3i km" % (full_route.length[-1]), color=route_color, transform=ccrs.PlateCarree(),
                 horizontalalignment='left')
    if show_current_elevation:
        plt.text(extent[0] + 0.5 * (extent[1] - extent[0]), extent[2] - 0.05 * (extent[3] - extent[2]),
                 "Elevation: %4i m" % (route.altitude[-1]), color=route_color, transform=ccrs.PlateCarree(),
                 horizontalalignment='center')
    if show_total_elevation:
        plt.text(extent[0] + 0.5 * (extent[1] - extent[0]), extent[2] - 0.05 * (extent[3] - extent[2]),
                 "Total elevation: %4i m" % (full_route.elevation_gain[-1]), color=route_color, transform=ccrs.PlateCarree(),
                 horizontalalignment='center')
    if show_current_speed:
        plt.text(extent[1] - 0.02 * (extent[1] - extent[0]), extent[2] - 0.05 * (extent[3] - extent[2]),
                 "Current speed: %2i km/h" % (np.nan_to_num(route.speed[-1])), color=route_color, transform=ccrs.PlateCarree(),
                 horizontalalignment='right')
    if show_avg_speed:
        plt.text(extent[1] - 0.02 * (extent[1] - extent[0]), extent[2] - 0.05 * (extent[3] - extent[2]),
                 "Average speed: %2i km/h" % (np.mean(np.nan_to_num(route.speed))), color=route_color, transform=ccrs.PlateCarree(),
                 horizontalalignment='right')
    if add_trail_flag:
        add_trail(ax, route, color=route_color)
    plt.axis('off')
    plt.tight_layout()
    if output_file is not None:
        plt.savefig("output/" + output_file)


def add_trail(ax, route, color='r'):
    if isinstance(route, SubRoute):
        route_length = route.full_route.max_index
    else:
        route_length = route.max_index
    alpha = np.zeros(route_length)
    trail_length = int(0.05*route_length)
    if route.max_index > trail_length:
        alpha[route.max_index - trail_length:route.max_index] = np.arange(trail_length).astype(float) / float(trail_length)
    else:
        alpha[0:route.max_index] = np.arange(route.max_index).astype(float) / float(route.max_index)
    colorfade = colors.to_rgb(color) + (0.0,)
    cmap = colors.LinearSegmentedColormap.from_list('my', [colorfade, color])
    points = np.vstack((route.longitude, route.latitude)).T.reshape(-1, 1, 2)
    segments = np.hstack((points[:-1], points[1:]))
    lc = LineCollection(segments, lw=3, zorder=10, transform=ccrs.PlateCarree(), array=alpha, cmap=cmap)
    ax.add_collection(lc)

