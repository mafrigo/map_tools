import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import matplotlib.animation as mani
import PIL
import yaml
from .route_reader import Route


ffmpeg_path = r"C:\Users\mfrigo\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"
frames_per_second = 30


def make_plot(route, zoomout_fac=0.8, color='r', add_real_map=False, add_cities_in_map=True, output_file='output.png', fig=None, map_extent="default"):
    if fig is None:
        fig = plt.figure(figsize=(7, 9))
        save_figure = True
    else:
        save_figure = False
    gs = GridSpec(3, 1, height_ratios=[3, 1, 1])
    ax0 = fig.add_subplot(gs[0])
    ax1 = fig.add_subplot(gs[1])
    ax2 = fig.add_subplot(gs[2])
    lat_route_diff = abs(np.max(route.latitude) - np.min(route.latitude))
    lon_route_diff = abs(np.max(route.longitude) - np.min(route.longitude))
    if map_extent == "default":
        map_extent = [[np.min(route.longitude) - lat_route_diff * zoomout_fac,
                      np.max(route.longitude) + lon_route_diff * zoomout_fac],
                      [np.min(route.latitude) - lat_route_diff * zoomout_fac,
                       np.max(route.latitude) + lat_route_diff * zoomout_fac]]
    if add_cities_in_map:
        add_cities(ax0, map_extent, color=color)
    if add_real_map:
        plot_europe_map(ax0, route.longitude, route.latitude, zoomout_fac=zoomout_fac)
    ax0.plot(route.longitude, route.latitude, color=color)
    ax0.set_xlim(map_extent[0])
    ax0.set_ylim(map_extent[1])
    ax0.set_ylabel("latitude")
    ax0.set_xlabel("longitude")
    ax0.axes.set_aspect('equal')
    ax1.plot(route.length, route.altitude, color=color)
    ax1.set_ylabel("elevation (m)")
    ax2.plot(route.length, route.speed, color=color)
    ax2.set_ylabel("speed (km/h)")
    ax2.set_xlabel("distance (km)")
    plt.tight_layout()
    if save_figure:
        plt.savefig(output_file)


def make_movie(routefile, zoomout_fac=0.8, color='r', add_real_map=False, add_cities_in_map=True, movie_file="movie"):
    plt.rcParams['animation.ffmpeg_path'] = ffmpeg_path
    FFMpegWriter = mani.writers['ffmpeg']
    metadata = dict(title=movie_file, artist='Matplotlib')
    writer = FFMpegWriter(fps=frames_per_second, metadata=metadata)
    fig = plt.figure(figsize=(7, 9))
    route = Route("test/Erding_Whirlpool.gpx")
    map_extent = [[np.min(route.longitude) - abs(np.max(route.latitude) - np.min(route.latitude)) * zoomout_fac,
                   np.max(route.longitude) + abs(np.max(route.longitude) - np.min(route.longitude)) * zoomout_fac],
                  [np.min(route.latitude) - abs(np.max(route.latitude) - np.min(route.latitude)) * zoomout_fac,
                   np.max(route.latitude) + abs(np.max(route.longitude) - np.min(route.longitude)) * zoomout_fac]]

    with writer.saving(fig, "output_video/" + movie_file + ".mp4", 100):
        for i in range(1, len(route.latitude)):
            route = Route(routefile, max_iter=i)
            make_plot(route,
                      zoomout_fac=zoomout_fac, color=color, add_real_map=add_real_map, add_cities_in_map=add_cities_in_map,
                      output_file="frame"+str(i)+".png", map_extent=map_extent, fig=fig)
            writer.grab_frame()
            plt.clf()



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
            textsize = 11
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
