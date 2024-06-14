import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as mani
import cartopy.io.img_tiles as cimgt
from .plotting import plot, get_frame_extent
from .config import get_yaml_config
from .route import Route, SubRoute

cfg = get_yaml_config()


def init_movie(output_file: str):
    plt.rcParams['animation.ffmpeg_path'] = cfg["ffmpeg_path"]
    plt.rcParams['savefig.bbox'] = "tight"
    metadata = dict(title=output_file, artist='Matplotlib')
    fig = plt.figure()
    writer = mani.FFMpegWriter(fps=cfg["frames_per_second"], metadata=metadata, extra_args=['-vcodec', 'libx264'])
    writer.setup(fig, output_file)
    osm = cimgt.OSM()
    return fig, writer, osm


def make_movie_with_static_map(route: Route | SubRoute, output_file: str = "movie", frame_step: int = 1, cut_at_frame: int = None):
    fig, writer, osm_request = init_movie(output_file)
    progress_counter = 0
    nframes = len(route.latitude)
    frame_step = get_frame_step_from_real_time(route)
    print("Using frame step: " + str(frame_step))
    with writer.saving(fig, "output/" + output_file + ".mp4", 100):
        for i in range(1, nframes, frame_step):
            subroute = route[0:i]
            plot(subroute, osm_request=osm_request, output_file="", extent=None, add_trail=True)
            writer.grab_frame()
            plt.clf()
            del subroute
            progress_counter += 1
            update_progress_bar(progress_counter, nframes, frame_step=frame_step)
            if cut_at_frame is not None:
                if i >= cut_at_frame:
                    break
    writer.finish()


def make_movie_with_dynamic_map(route: Route | SubRoute, map_frame_size_in_deg: float = 0.1, output_file: str = "movie",
                                frame_step: int = 1, cut_at_frame: int = None, final_zoomout: bool = True):
    fig, writer, osm_request = init_movie(output_file)
    progress_counter = 0
    nframes = len(route.latitude)
    frame_step = get_frame_step_from_real_time(route)
    with writer.saving(fig, "output/" + output_file + ".mp4", 100):
        for i in range(1, nframes, frame_step):
            subroute = route[0:i]
            if i > 5:
                extent = get_frame_extent(subroute, fixed_size=map_frame_size_in_deg, center_on="last_smooth")
            else:
                extent = get_frame_extent(subroute, fixed_size=map_frame_size_in_deg, center_on="last")
            plot(subroute, osm_request=osm_request, output_file="", extent=extent, add_trail=True)
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
                current_extent = [
                    initial_extent[j] + (float(i) / cfg["zoomout_nframes"]) * (final_extent[j] - initial_extent[j]) for
                    j in range(len(initial_extent))]
                plot(route, osm_request=osm_request, output_file="", extent=current_extent, add_trail=False)
                writer.grab_frame()
                plt.clf()
                progress_counter += 1
                update_progress_bar(progress_counter, cfg["zoomout_nframes"] + cfg["still_final_nframes"])
            for i in range(cfg["still_final_nframes"]):
                plot(route, osm_request=osm_request, output_file="", extent=final_extent, add_trail=False)
                writer.grab_frame()
                plt.clf()
                progress_counter += 1
                update_progress_bar(progress_counter, cfg["zoomout_nframes"] + cfg["still_final_nframes"])


def get_frame_step_from_real_time(route: Route | SubRoute):
    #note: this only works if the timestep is constant; an interpolation approach would be more general
    real_time_step_in_seconds = np.mean(route.get_time_intervals())
    return int(60. * cfg["real_minutes_per_video_second"] / (cfg["frames_per_second"] * real_time_step_in_seconds))


def update_progress_bar(progress_counter: int, nframes: int, frame_step: int = 1):
    progress = 100 * progress_counter / nframes
    sys.stdout.write('\r')
    sys.stdout.write("[{:{}}] {:.1f}%".format("=" * int(frame_step * progress / 2.), 50, frame_step * progress))
    sys.stdout.flush()
