import sys
import matplotlib.pyplot as plt
import matplotlib.animation as mani
from .plotting import get_frame_extent
from .movie_frame import plot_frame
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
    return fig, writer


def make_movie_with_static_map(route: Route | SubRoute, output_file: str = "movie", cut_at_frame: int = None):
    fig, writer = init_movie(output_file)
    progress_counter = 0
    nframes = len(route.latitude)
    frame_step = get_frame_step_from_real_time(route)
    print("Using frame step: " + str(frame_step))
    extent = get_frame_extent(route.full_route)
    with writer.saving(fig, "output/" + output_file + ".mp4", 100):
        for i in range(1, nframes, frame_step):
            subroute = route[0:i]
            plot_frame(subroute, extent=extent)
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
                                cut_at_frame: int = None, final_zoomout: bool = True):
    fig, writer = init_movie(output_file)
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
            plot_frame(subroute, extent=extent)
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
                plot_frame(route, extent=current_extent)
                writer.grab_frame()
                plt.clf()
                progress_counter += 1
                update_progress_bar(progress_counter, cfg["zoomout_nframes"] + cfg["still_final_nframes"])
            for i in range(cfg["still_final_nframes"]):
                plot_frame(route, extent=final_extent)
                writer.grab_frame()
                plt.clf()
                progress_counter += 1
                update_progress_bar(progress_counter, cfg["zoomout_nframes"] + cfg["still_final_nframes"])


def get_frame_step_from_real_time(route: Route | SubRoute):
    #note: this only works if the timestep is constant; an interpolation approach would be more general
    return int(cfg["real_seconds_per_video_second"] / (cfg["frames_per_second"] * route.avg_timestep))


def update_progress_bar(progress_counter: int, nframes: int, frame_step: int = 1):
    progress = 100 * progress_counter / nframes
    sys.stdout.write('\r')
    sys.stdout.write("[{:{}}] {:.1f}%".format("=" * int(frame_step * progress / 2.), 50, frame_step * progress))
    sys.stdout.flush()
