import sys
import matplotlib.pyplot as plt
import matplotlib.animation as mani
import cartopy.io.img_tiles as cimgt
from .plotting import plot_route_on_map, get_frame_extent
from .config import get_yaml_config

cfg = get_yaml_config()


def init_movie(output_file):
    plt.rcParams['animation.ffmpeg_path'] = cfg["ffmpeg_path"]
    FFMpegWriter = mani.writers['ffmpeg']
    metadata = dict(title=output_file, artist='Matplotlib')
    writer = FFMpegWriter(fps= cfg["frames_per_second"], metadata=metadata)
    fig = plt.figure(figsize=(7, 10))
    osm = cimgt.OSM()
    return fig, writer, osm


def make_movie(route, output_file="movie", frame_step=1, delta_if_centered=None, cut_at_frame=None, final_zoomout=True):
    fig, writer, osm_request = init_movie(output_file)
    progress_counter = 0
    nframes = len(route.latitude)
    with writer.saving(fig, "output/" + output_file + ".mp4", 100):
        for i in range(1, nframes, frame_step):
            subroute = route[0:i]
            if delta_if_centered is not None:
                extent = get_frame_extent(subroute, fixed_size=delta_if_centered, center_on_last=True)
            else:
                extent = None
            plot_route_on_map(subroute, osm_request=osm_request, output_file=None, extent=extent)
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
            final_extent = get_frame_extent(route)
            progress_counter = 0
            for i in range(cfg["zoomout_nframes"]):
                current_extent = [initial_extent[j] + (float(i)/cfg["zoomout_nframes"])*(final_extent[j] - initial_extent[j]) for j in range(len(initial_extent))]
                plot_route_on_map(route, osm_request=osm_request, output_file=None, extent=current_extent)
                writer.grab_frame()
                plt.clf()
                progress_counter += 1
                update_progress_bar(progress_counter, cfg["zoomout_nframes"] + cfg["still_final_nframes"])
            for i in range(cfg["still_final_nframes"]):
                plot_route_on_map(route, osm_request=osm_request, output_file=None, extent=final_extent)
                writer.grab_frame()
                plt.clf()
                progress_counter += 1
                update_progress_bar(progress_counter, cfg["zoomout_nframes"] + cfg["still_final_nframes"])


def update_progress_bar(progress_counter, nframes, frame_step=1):
    progress = 100 * progress_counter / nframes
    sys.stdout.write('\r')
    sys.stdout.write(
        "[{:{}}] {:.1f}%".format("=" * int(frame_step * progress / (100 / cfg["progress_bar_length"])), cfg["progress_bar_length"],
                                 frame_step * progress))
    sys.stdout.flush()
