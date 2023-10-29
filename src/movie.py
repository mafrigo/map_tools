import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as mani
import cartopy.io.img_tiles as cimgt
from .plotting import plot_route_on_map


ffmpeg_path = r"C:\Users\mfrigo\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"
frames_per_second = 30
progress_bar_length = 50
zoomout_nframes = 180
still_final_frames = 30


def make_movie(route, zoomout_fac=0.8, color='r', output_file="movie", frame_step=1, delta_if_centered=None, cut_at_frame=None, final_zoomout=True):
    plt.rcParams['animation.ffmpeg_path'] = ffmpeg_path
    FFMpegWriter = mani.writers['ffmpeg']
    metadata = dict(title=output_file, artist='Matplotlib')
    writer = FFMpegWriter(fps=frames_per_second, metadata=metadata)
    fig = plt.figure(figsize=(7, 10))
    progress_counter = 0
    nframes = len(route.latitude)
    osm_request = cimgt.OSM()
    with writer.saving(fig, "output/" + output_file + ".mp4", 100):
        for i in range(1, nframes, frame_step):
            subroute = route[0:i]
            if delta_if_centered is not None:
                extent = [subroute.longitude[-1] - 0.5 * delta_if_centered * (1. + zoomout_fac),
                          subroute.longitude[-1] + 0.5 * delta_if_centered * (1. + zoomout_fac),
                          subroute.latitude[-1] - 0.25 * delta_if_centered * (1. + zoomout_fac),
                          subroute.latitude[-1] + 0.25 * delta_if_centered * (1. + zoomout_fac)]
            else:
                extent = None
            plot_route_on_map(subroute, osm_request=osm_request, zoomout_fac=zoomout_fac, route_color=color,
                              output_file=None, extent=extent)
            writer.grab_frame()
            plt.clf()
            del subroute
            progress_counter += 1
            update_progress_bar(progress_counter, nframes, frame_step=frame_step)
            if cut_at_frame is not None:
                if i >= cut_at_frame:
                    break
        if final_zoomout:
            print("\nRendering final zoomout")
            initial_extent = extent
            lat_route_diff = abs(np.max(route.latitude) - np.min(route.latitude))
            lon_route_diff = abs(np.max(route.longitude) - np.min(route.longitude))
            lon_size = np.max([2*lat_route_diff, lon_route_diff])
            final_extent = [np.min(route.longitude) - lon_size * zoomout_fac,
                  np.max(route.longitude) + lon_size * zoomout_fac,
                  np.min(route.latitude) - lon_size * zoomout_fac,
                  np.max(route.latitude) + lon_size * zoomout_fac]
            progress_counter = 0
            for i in range(zoomout_nframes):
                current_extent = [initial_extent[j] + (float(i)/zoomout_nframes)*(final_extent[j] - initial_extent[j]) for j in range(len(initial_extent))]
                plot_route_on_map(route, osm_request=osm_request, zoomout_fac=zoomout_fac, route_color=color,
                                  output_file=None, extent=current_extent)
                writer.grab_frame()
                plt.clf()
                progress_counter += 1
                update_progress_bar(progress_counter, zoomout_nframes + still_final_frames)
            for i in range(still_final_frames):
                plot_route_on_map(route, osm_request=osm_request, zoomout_fac=zoomout_fac, route_color=color,
                                  output_file=None, extent=final_extent)
                writer.grab_frame()
                plt.clf()
                progress_counter += 1
                update_progress_bar(progress_counter, zoomout_nframes + still_final_frames)


def update_progress_bar(progress_counter, nframes, frame_step=1):
    progress = 100 * progress_counter / nframes
    sys.stdout.write('\r')
    sys.stdout.write(
        "[{:{}}] {:.1f}%".format("=" * int(frame_step * progress / (100 / progress_bar_length)), progress_bar_length,
                                 progress))
    sys.stdout.flush()
