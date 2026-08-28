import io
import sys
from typing import List, Tuple

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as mani

import cartopy.crs as ccrs

from .plotting import (
    get_frame_extent,
    get_frame_extent_multiple,
    create_background_map,
    prefetch_tiles,
)
from .movie_frame import plot_frame, get_dynamic_frame_extent_for_multiple_routes
from .config import get_yaml_config
from .route import Route

cfg = get_yaml_config()


def init_movie(output_file: str) -> Tuple[plt.Figure, mani.FFMpegWriter]:
    plt.rcParams["animation.ffmpeg_path"] = cfg["ffmpeg_path"]
    metadata = dict(title=output_file, artist="Matplotlib")
    fig = plt.figure()
    writer = mani.FFMpegWriter(
        fps=cfg["frames_per_second"],
        metadata=metadata,
        extra_args=[
            "-vcodec", "libx264",
            "-preset", cfg.get("ffmpeg_preset", "veryfast"),
            "-crf", str(cfg.get("ffmpeg_crf", 18)),
        ],
    )
    writer.setup(fig, output_file)
    return fig, writer


def make_movie_with_static_map(
        route: Route,
        output_file: str = "movie",
        real_seconds_per_video_second: float = 150.0
) -> None:
    fig, writer = init_movie(output_file)
    progress_counter = 0
    nframes = len(route.latitude)
    frame_step = get_frame_step_from_real_time(route, real_seconds_per_video_second)
    print("Using frame step: " + str(frame_step))
    extent = get_frame_extent(route.full_route)
    prefetch_tiles([extent])
    with writer.saving(fig, "output/" + output_file + ".mp4", cfg["video_dpi_resolution"]):
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
        real_seconds_per_video_second: float = 150.0
) -> None:
    fig, writer = init_movie(output_file)
    progress_counter = 0
    nframes = len(route.latitude)
    frame_step = get_frame_step_from_real_time(route, real_seconds_per_video_second)
    frame_indices = range(1, nframes, frame_step)
    # plan phase: compute all frame extents up front (cheap) so the required
    # map tiles can be downloaded in parallel before any frame is rendered
    frame_extents = []
    for i in frame_indices:
        subroute = route[0:i]
        center_mode = "last_smooth" if i > cfg["frames_per_second"] else "last"
        frame_extents.append(
            get_frame_extent(subroute, fixed_size=map_frame_size_in_deg, center_on=center_mode)
        )
        del subroute
    zoomout_frames = cfg["movie_zoomout_seconds"] * cfg["frames_per_second"]
    still_frames = cfg["still_final_seconds"] * cfg["frames_per_second"]
    if final_zoomout:
        final_extent = get_frame_extent(route)
        initial_extent = frame_extents[-1] if len(frame_extents) > 0 else final_extent
        zoomout_extents = [
            [initial_extent[j] + (float(i) / zoomout_frames) * (final_extent[j] - initial_extent[j])
             for j in range(len(initial_extent))]
            for i in range(zoomout_frames)
        ]
        prefetch_tiles(frame_extents + zoomout_extents + [final_extent])
    else:
        final_extent = None
        prefetch_tiles(frame_extents)
    with writer.saving(fig, "output/" + output_file + ".mp4", cfg["video_dpi_resolution"]):
        for i, extent in zip(frame_indices, frame_extents):
            subroute = route[0:i]
            plot_frame(subroute, writer, extent=extent)
            del subroute
            progress_counter += 1
            update_progress_bar(progress_counter, nframes, frame_step=frame_step)
        if final_zoomout:
            print("\nRendering final zoomout")
            for extent in zoomout_extents:
                plot_frame(route, writer, extent=extent, include_trail=False, show_avg_speed=True)
                progress_counter += 1
                update_progress_bar(progress_counter, zoomout_frames + still_frames)
            # the final still frames are identical: render once, duplicate in the video
            plot_frame(route, None, extent=final_extent, include_trail=False, show_avg_speed=True)
            render_and_duplicate_frame(fig, writer, still_frames)
            for i in range(still_frames):
                update_progress_bar(i + 1, zoomout_frames + still_frames)


def make_movie_with_multiple_routes(
        routes: List[Route],
        min_map_frame_size_in_deg: float = cfg["default_min_frame_size_in_deg"],
        dynamic_frame: bool = True,
        use_real_time: bool = True,
        output_file: str = "race_movie",
        final_zoomout: bool = True,
        real_seconds_per_video_second: float = 150.0
) -> None:
    fig, writer = init_movie(output_file)
    progress_counter = 0
    nframes = 0
    current_time_in_seconds = 0
    routes_finished = [False] * len(routes)
    routes_paused = [False] * len(routes)
    previous_frame_index = [0] * len(routes)
    current_subroutes = [route[0:1] for route in routes]
    if use_real_time:
        for route in routes:
            if route.time[-1] / (real_seconds_per_video_second / cfg["frames_per_second"]) > nframes:
                nframes = route.time[-1] / (real_seconds_per_video_second / cfg["frames_per_second"])
    else:
        for route in routes:
            route.frame_step = get_frame_step_from_real_time(route, real_seconds_per_video_second)
            if len(route.latitude) / route.frame_step > nframes:
                nframes = int(len(route.latitude) / route.frame_step)

    # plan phase: compute the extent and subroutes of every frame up front
    # (cheap) so the required map tiles can be downloaded in parallel first
    frame_plan = []
    current_frame = 0
    if not dynamic_frame:
        static_extent = get_frame_extent_multiple(routes)
    while False in routes_finished:
        current_frame += 1
        current_time_in_seconds += real_seconds_per_video_second / cfg["frames_per_second"]
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
                current_subroutes[route_id] = route[0: frame_index]
            routes_to_be_plotted.append(current_subroutes[route_id])
        if False in routes_paused:
            if dynamic_frame:
                extent = get_dynamic_frame_extent_for_multiple_routes(
                    routes_to_be_plotted, min_size_in_deg=min_map_frame_size_in_deg
                )
            else:
                extent = static_extent
            frame_plan.append((extent, list(routes_to_be_plotted), current_time_in_seconds))
    prefetch_tiles([plan_entry[0] for plan_entry in frame_plan])

    zoomout_frames = cfg["movie_zoomout_seconds"] * cfg["frames_per_second"]
    still_frames = cfg["still_final_seconds"] * cfg["frames_per_second"]
    with writer.saving(fig, "output/" + output_file + ".mp4", cfg["video_dpi_resolution"]):
        for extent, subroutes, frame_time in frame_plan:
            create_background_map(extent)
            route_counter = 0
            for subroute in subroutes:
                plot_frame(
                    subroute,
                    None,
                    extent=extent,
                    plot_background_map=False,
                    add_data=False,
                    zorder_modifier=2 * route_counter,
                )
                del subroute
                route_counter += 1
            plot_global_time(extent, frame_time)
            writer.grab_frame()
            plt.clf()
            progress_counter += 1
            update_progress_bar(progress_counter, nframes, frame_step=1)
        if final_zoomout and len(frame_plan) > 0:
            print("\nRendering final zoomout")
            initial_extent = frame_plan[-1][0]
            final_extent = get_frame_extent_multiple(routes)
            zoomout_extents = [
                [initial_extent[j] + (float(i) / zoomout_frames) * (final_extent[j] - initial_extent[j])
                 for j in range(len(initial_extent))]
                for i in range(zoomout_frames)
            ]
            prefetch_tiles(zoomout_extents + [final_extent])
            for extent in zoomout_extents:
                create_background_map(extent)
                route_counter = 0
                for route in routes:
                    plot_frame(
                        route,
                        None,
                        extent=extent,
                        plot_background_map=False,
                        add_data=False,
                        include_trail=False,
                        zorder_modifier=2 * route_counter,
                    )
                    route_counter += 1
                writer.grab_frame()
                plt.clf()
                progress_counter += 1
                update_progress_bar(progress_counter, zoomout_frames + still_frames)
            create_background_map(final_extent)
            route_counter = 0
            for route in routes:
                plot_frame(
                    route,
                    None,
                    extent=final_extent,
                    plot_background_map=False,
                    add_data=False,
                    include_trail=False,
                    zorder_modifier=2 * route_counter,
                )
                route_counter += 1
            render_and_duplicate_frame(fig, writer, still_frames)
            for i in range(still_frames):
                update_progress_bar(i + 1, zoomout_frames + still_frames)


def render_and_duplicate_frame(fig: plt.Figure, writer: mani.FFMpegWriter, n_frames: int) -> None:
    """Render the current figure once and emit it n_frames times.

    Identical consecutive frames (e.g. the final still section of a movie) do
    not need to be re-rendered: the raw frame is written to the ffmpeg pipe
    repeatedly instead.
    """
    if n_frames <= 0:
        plt.clf()
        return
    try:
        buffer = io.BytesIO()
        fig.savefig(buffer, format=writer.frame_format, dpi=writer.dpi)
        raw_frame = buffer.getvalue()
        for _ in range(n_frames):
            writer._proc.stdin.write(raw_frame)
    except AttributeError:
        for _ in range(n_frames):
            writer.grab_frame()
    plt.clf()


def get_frame_step_from_real_time(route: Route, real_seconds_per_video_second: float) -> int:
    # note: this only works if the timestep is constant; an interpolation approach would be more general
    try:
        frame_step = int(np.round(
            real_seconds_per_video_second
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


def plot_global_time(extent: List[float], current_time_in_seconds: int):
    days = int(current_time_in_seconds / (24. * 60. * 60.))
    hours = int((current_time_in_seconds - days * 24. * 60. * 60.) / (60. * 60.))
    minutes = int((current_time_in_seconds - days * 24. * 60. * 60. - hours * 60. * 60.) / 60.)
    plt.text(
        extent[0] + 0.5 * (extent[1] - extent[0]),
        extent[2] - 0.026 * (extent[3] - extent[2]),
        "%i days %i hours %i minutes" % (days, hours, minutes),
        color=cfg["text_color"],
        transform=ccrs.PlateCarree(),
        horizontalalignment="center",
        fontsize=8
    )
