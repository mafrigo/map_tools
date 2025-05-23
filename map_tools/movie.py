import sys
from typing import List, Tuple
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as mani
from .plotting import get_frame_extent, get_frame_extent_multiple, create_background_map
from .movie_frame import plot_frame, get_dynamic_frame_extent_for_multiple_routes
from .config import get_yaml_config
from .route import Route

cfg = get_yaml_config()


def init_movie(output_file: str) -> Tuple[plt.Figure, mani.FFMpegWriter]:
    plt.rcParams["animation.ffmpeg_path"] = cfg["ffmpeg_path"]
    plt.rcParams["savefig.bbox"] = "tight"
    metadata = dict(title=output_file, artist="Matplotlib")
    fig = plt.figure()
    writer = mani.FFMpegWriter(
        fps=cfg["frames_per_second"],
        metadata=metadata,
        extra_args=["-vcodec", "libx264"],
    )
    writer.setup(fig, output_file)
    return fig, writer


def make_movie_with_static_map(
    route: Route, output_file: str = "movie"
) -> None:
    fig, writer = init_movie(output_file)
    progress_counter = 0
    nframes = len(route.latitude)
    frame_step = get_frame_step_from_real_time(route)
    print("Using frame step: " + str(frame_step))
    extent = get_frame_extent(route.full_route)
    with writer.saving(fig, "output/" + output_file + ".mp4", 100):
        for i in range(1, nframes, frame_step):
            subroute = route[0:i]
            plot_frame(subroute, writer, extent=extent)
            del subroute
            progress_counter += 1
            update_progress_bar(progress_counter, nframes, frame_step=frame_step)
    writer.finish()


def make_movie_with_dynamic_map(
    route: Route,
    map_frame_size_in_deg: float = 0.1,
    output_file: str = "movie",
    final_zoomout: bool = True,
) -> None:
    fig, writer = init_movie(output_file)
    progress_counter = 0
    nframes = len(route.latitude)
    frame_step = get_frame_step_from_real_time(route)
    with writer.saving(fig, "output/" + output_file + ".mp4", cfg["video_dpi_resolution"]):
        for i in range(1, nframes, frame_step):
            subroute = route[0:i]
            if i > cfg["frames_per_second"]:
                extent = get_frame_extent(
                    subroute, fixed_size=map_frame_size_in_deg, center_on="last_smooth"
                )
            else:
                extent = get_frame_extent(
                    subroute, fixed_size=map_frame_size_in_deg, center_on="last"
                )
            plot_frame(subroute, writer, extent=extent)
            del subroute
            progress_counter += 1
            update_progress_bar(progress_counter, nframes, frame_step=frame_step)
        if final_zoomout:
            print("\nRendering final zoomout")
            initial_extent = extent
            final_extent = get_frame_extent(route)
            progress_counter = 0
            for i in range(cfg["movie_zoomout_seconds"] * cfg["frames_per_second"]):
                current_extent = [
                    initial_extent[j]
                    + (float(i) / (cfg["movie_zoomout_seconds"] * cfg["frames_per_second"]))
                    * (final_extent[j] - initial_extent[j])
                    for j in range(len(initial_extent))
                ]
                plot_frame(route, writer, extent=current_extent)
                progress_counter += 1
                update_progress_bar(
                    progress_counter,
                    cfg["movie_zoomout_seconds"] * cfg["frames_per_second"]
                    + cfg["still_final_seconds"] * cfg["frames_per_second"],
                )
            for i in range(cfg["still_final_seconds"] * cfg["frames_per_second"]):
                plot_frame(route, writer, extent=final_extent)
                progress_counter += 1
                update_progress_bar(
                    progress_counter,
                    cfg["movie_zoomout_seconds"] * cfg["frames_per_second"]
                    + cfg["still_final_seconds"] * cfg["frames_per_second"],
                )


def make_movie_with_multiple_routes(
    routes: List[Route],
    min_map_frame_size_in_deg: float = cfg["default_min_frame_size_in_deg"],
    dynamic_frame: bool = True,
    use_real_time: bool = True,
    output_file: str = "race_movie",
    final_zoomout: bool = True,
) -> None:
    import cartopy.crs as ccrs
    fig, writer = init_movie(output_file)
    progress_counter = 0
    nframes = 0
    current_time_in_seconds = 0
    routes_finished = [False]*len(routes)
    routes_paused = [False]*len(routes)
    previous_frame_index = [0]*len(routes)
    current_subroutes = [route[0:1] for route in routes]
    if use_real_time:
        for route in routes:
            if route.time[-1]/(cfg["real_seconds_per_video_second"]/cfg["frames_per_second"]) > nframes:
                nframes = route.time[-1]/(cfg["real_seconds_per_video_second"]/cfg["frames_per_second"])
    else:
        for route in routes:
            route.frame_step = get_frame_step_from_real_time(route)
            if len(route.latitude) / route.frame_step > nframes:
                nframes = int(len(route.latitude) / route.frame_step)

    if not dynamic_frame:
        extent = get_frame_extent_multiple(routes)
    current_frame = 0
    with writer.saving(fig, "output/" + output_file + ".mp4", 100):
        while False in routes_finished:
            current_frame += 1
            if use_real_time:
                current_time_in_seconds += cfg["real_seconds_per_video_second"]/cfg["frames_per_second"]
            routes_to_be_plotted = []
            for route_id in range(len(routes)):
                route = routes[route_id]
                if routes_finished[route_id]:
                    routes_to_be_plotted.append(route)
                    routes_paused[route_id] = True
                    continue
                if use_real_time:
                    if route.time[0] > current_time_in_seconds:
                        routes_paused[route_id] = True
                        continue
                    frame_index = np.searchsorted(route.time, current_time_in_seconds, side="left")
                    routes_paused[route_id] = False
                    if previous_frame_index[route_id] == frame_index:
                        routes_paused[route_id] = True
                    previous_frame_index[route_id] = frame_index
                else:
                    frame_index = current_frame * route.frame_step
                if frame_index >= len(route):
                    routes_finished[route_id] = True
                if frame_index > 0:
                    current_subroutes[route_id] = route[0 : frame_index]
                routes_to_be_plotted.append(current_subroutes[route_id])
            if False in routes_paused:
                if dynamic_frame:
                    extent = get_dynamic_frame_extent_for_multiple_routes(
                        routes_to_be_plotted, min_size_in_deg=min_map_frame_size_in_deg
                    )
                create_background_map(extent)
                for subroute in routes_to_be_plotted:
                    plot_frame(
                        subroute,
                        None,
                        extent=extent,
                        plot_background_map=False,
                        add_data=False,
                    )
                    del subroute
                plt.text(
                    extent[0] + 0.5 * (extent[1] - extent[0]),
                    extent[2] - 0.026 * (extent[3] - extent[2]),
                    "Minutes: %i" % (current_time_in_seconds/60.),
                    color=cfg["text_color"],
                    transform=ccrs.PlateCarree(),
                    horizontalalignment="center",
                    fontsize=8
                )
                writer.grab_frame()
                plt.clf()
                progress_counter += 1
            update_progress_bar(progress_counter, nframes, frame_step=1)
        if final_zoomout:
            print("\nRendering final zoomout")
            initial_extent = extent
            final_extent = get_frame_extent_multiple(routes)
            progress_counter = 0
            for i in range(cfg["movie_zoomout_seconds"] * cfg["frames_per_second"]):
                current_extent = [
                    initial_extent[j]
                    + (float(i) / (cfg["movie_zoomout_seconds"] * cfg["frames_per_second"]))
                    * (final_extent[j] - initial_extent[j])
                    for j in range(len(initial_extent))
                ]
                create_background_map(current_extent)
                for route in routes:
                    plot_frame(
                        route,
                        None,
                        extent=current_extent,
                        plot_background_map=False,
                        add_data=False,
                    )
                writer.grab_frame()
                plt.clf()
                progress_counter += 1
                update_progress_bar(
                    progress_counter,
                    cfg["movie_zoomout_seconds"] * cfg["frames_per_second"]
                    + cfg["still_final_seconds"] * cfg["frames_per_second"],
                )
            for i in range(cfg["still_final_seconds"] * cfg["frames_per_second"]):
                create_background_map(final_extent)
                for route in routes:
                    plot_frame(
                        route,
                        None,
                        extent=final_extent,
                        plot_background_map=False,
                        add_data=False,
                    )
                writer.grab_frame()
                plt.clf()
                progress_counter += 1
                update_progress_bar(
                    progress_counter,
                    cfg["movie_zoomout_seconds"] * cfg["frames_per_second"]
                    + cfg["still_final_seconds"] * cfg["frames_per_second"],
                )


def get_frame_step_from_real_time(route: Route) -> int:
    # note: this only works if the timestep is constant; an interpolation approach would be more general
    try:
        frame_step = int(np.round(
            cfg["real_seconds_per_video_second"]
            / (cfg["frames_per_second"] * route.avg_timestep)
        ))
    except OverflowError:
        print("Warning: failure to calculate optimal frame step - is time data missing?")
        return 1
    if frame_step > 0:
        return frame_step
    else:
        print("Warning: not enough data points for selected frame rate")
        return 1


def update_progress_bar(progress_counter: int, nframes: int, frame_step: int = 1) -> None:
    progress = 100 * progress_counter / nframes
    sys.stdout.write("\r")
    sys.stdout.write(
        "[{:{}}] {:.1f}%".format(
            "=" * int(frame_step * progress / 2.0), 50, frame_step * progress
        )
    )
    sys.stdout.flush()
