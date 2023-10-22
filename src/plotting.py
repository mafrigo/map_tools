import numpy as np
import matplotlib.pyplot as plt
import PIL
import yaml


def make_plot(route, zoomout_fac=0.8, add_real_map=False, add_cities_in_map=True):
    fix, (ax0, ax1) = plt.subplots(2, 1, height_ratios=[3, 1])
    lat_route_diff = abs(np.max(route.latitude) - np.min(route.latitude))
    lon_route_diff = abs(np.max(route.longitude) - np.min(route.longitude))
    map_extent = [[np.min(route.longitude) - lat_route_diff * zoomout_fac,
                  np.max(route.longitude) + lon_route_diff * zoomout_fac],
                  [np.min(route.latitude) - lat_route_diff * zoomout_fac,
                   np.max(route.latitude) + lat_route_diff * zoomout_fac]]
    if add_cities_in_map:
        add_cities(ax0, map_extent, color='r')
    if add_real_map:
        plot_europe_map(ax0, route.longitude, route.latitude, zoomout_fac=zoomout_fac)
    ax0.plot(route.longitude, route.latitude, color='r')
    ax0.set_xlim(map_extent[0])
    ax0.set_ylim(map_extent[1])
    ax0.set_ylabel("latitude")
    ax0.set_xlabel("longitude")
    ax0.axes.set_aspect('equal')
    ax1.plot(route.length, route.altitude, color='r')
    ax1.set_ylabel("elevation (m)")
    ax1.set_xlabel("distance (km)")
    # plt.plot(route.length, route.speed)
    plt.tight_layout()
    plt.show()


def add_cities(ax, map_extent, color='r'):
    lat_route_diff = map_extent[1][1] - map_extent[1][0]
    with open("data/cities.yaml", "r") as ymlfile:
        cities = yaml.load(ymlfile, Loader=yaml.FullLoader)
    print(cities['Garching'].keys())
    for city in cities.keys():

        if cities[city]["lat"] > map_extent[1][1] or cities[city]["lat"] < map_extent[1][0] or cities[city]["lon"] > map_extent[0][1] or cities[city]["lon"] < map_extent[0][0]:
            break
        if cities[city]['size'] == 'small':
            marker = '.'
            textsize = 12
        elif cities[city]['size'] == 'big':
            marker = 's'
            textsize = 15
        else:
            raise IOError("Something went wrong")
        ax.scatter(cities[city]['lon'], cities[city]['lat'], color=color, marker=marker)
        ax.text(cities[city]['lon'], cities[city]['lat'] + 0.05 * lat_route_diff, city, color=color,
                horizontalalignment='center', fontsize=textsize)


def plot_europe_map(ax, longitude, latitude, zoomout_fac=0.8):
    PIL.Image.MAX_IMAGE_PIXELS = 999999999
    img = plt.imread('data/europe-high-resolution-map.webp')
    map_min_lat = 33.15
    map_max_lat = 73.13  # 72.4
    map_min_lon = -26.7
    map_max_lon = 56.5  # 56.26
    # latitude = np.array([35., 50.])  # Italy + Munich
    # longitude = np.array([6., 18.])  # Italy + Munich
    lat_map_diff = abs(map_max_lat - map_min_lat)
    lon_map_diff = abs(map_max_lon - map_min_lon)
    lat_route_diff = abs(np.max(latitude) - np.min(latitude))
    lon_route_diff = abs(np.max(longitude) - np.min(longitude))
    route_min_lat = np.min(latitude) - lat_route_diff * zoomout_fac
    route_max_lat = np.max(latitude) + lat_route_diff * zoomout_fac
    route_min_lon = np.min(longitude) - lon_route_diff * zoomout_fac
    route_max_lon = np.max(longitude) + lon_route_diff * zoomout_fac
    route_min_lat_pixel = ((route_min_lat - map_min_lat) / lat_map_diff * img.shape[1]).astype(int)
    route_max_lat_pixel = ((route_max_lat - map_min_lat) / lat_map_diff * img.shape[1]).astype(int)
    route_min_lon_pixel = ((route_min_lon - map_min_lon) / lon_map_diff * img.shape[0]).astype(int)
    route_max_lon_pixel = ((route_max_lon - map_min_lon) / lon_map_diff * img.shape[0]).astype(int)
    pixel_lat_lims = [img.shape[1] - route_max_lat_pixel, img.shape[1] - route_min_lat_pixel]
    pixel_lon_lims = [img.shape[0] - route_max_lon_pixel, img.shape[0] - route_min_lon_pixel]
    cut_image = img[pixel_lat_lims[0]:pixel_lat_lims[1], pixel_lon_lims[0]:pixel_lon_lims[1], :]
    print(np.min(longitude), np.max(longitude), np.min(latitude), np.max(latitude))
    print(route_min_lon, route_max_lon, route_min_lat, route_max_lat)
    print(route_min_lon_pixel, route_max_lon_pixel, route_min_lat_pixel, route_max_lat_pixel)
    ax.imshow(cut_image, extent=[route_min_lon, route_max_lon, route_min_lat, route_max_lat])
