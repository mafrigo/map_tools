import numpy as np
from datetime import datetime
from .config import get_yaml_config

cfg = get_yaml_config()


class Route(object):
    file: str
    latitude: np.ndarray
    longitude: np.ndarray
    altitude: np.ndarray
    time: np.ndarray
    n_gps_entries: int
    length_segments: np.ndarray
    length: np.ndarray
    time_intervals: np.ndarray
    speed: np.ndarray
    avg_speed: np.ndarray
    elevation_gain: np.ndarray
    max_index: int
    route_segment_id: np.ndarray
    avg_timestep: int = 1
    full_route: "Route"
    color: str = cfg["default_route_color"]
    display_name: str = ""
    frame_step: int = 1

    def __init__(
        self,
        file: str = "",
        color: str = cfg["default_route_color"],
        display_name: str = "",
        time_delay: int = 0
    ) -> None:
        if len(file) > 0:
            self.route_from_file(file, time_delay)
        self.full_route = self
        self.color = color
        self.display_name = display_name

    def route_from_file(self, file: str, time_delay: int = 0) -> None:
        self.file = file
        if file.endswith(".gpx"):
            route_array = self.read_gpx()
        else:
            raise IOError("Only .gpx files are currently supported")
        self.latitude = route_array[:, 0]
        self.longitude = route_array[:, 1]
        self.altitude = route_array[:, 2]
        self.time = route_array[:, 3] + time_delay
        self.n_gps_entries = len(self.latitude)
        self.length_segments = self.get_length_segments()
        self.length = self.get_length()
        self.time_intervals = self.get_time_intervals()
        self.speed = self.get_speed()
        self.avg_speed = self.get_avg_speed()
        self.elevation_gain = self.get_elevation_gain()
        self.max_index = len(self.latitude)
        self.route_segment_id = self.get_route_segments()
        self.avg_timestep = np.median(self.time_intervals)

    def __add__(self, other: "Route") -> "Route":
        return add_routes(self, other)

    def get_length_segments(self) -> np.ndarray:
        lat_to_km = 110.574
        lon_to_km = 111.320 * np.cos(self.latitude[1:] * np.pi / 180.0)
        length_array = np.zeros(self.n_gps_entries)
        length_array[1:] = np.sqrt(
            (lat_to_km * (self.latitude[1:] - self.latitude[:-1])) ** 2
            + (lon_to_km * (self.longitude[1:] - self.longitude[:-1])) ** 2
        )
        return length_array  # in km

    def get_elevation_gain(self) -> np.ndarray:
        elev_array = np.zeros(self.n_gps_entries)
        elev_array[1:] = self.altitude[1:] - self.altitude[:-1]
        return np.cumsum(np.clip(elev_array, 0.0, None))  # in m

    def get_length(self) -> np.ndarray:
        return np.cumsum(self.length_segments)  # in km

    def get_time_intervals(self) -> np.ndarray:
        time_array = np.zeros(self.n_gps_entries)
        time_array[1:] = self.time[1:] - self.time[:-1]
        return time_array

    def get_avg_speed(self) -> np.ndarray:
        return np.nan_to_num(self.length / (self.time / 3600.0))  # in km/h

    def get_speed(self) -> np.ndarray:
        return np.nan_to_num(
            self.length_segments / (self.time_intervals / 3600.0)
        )  # in km/h

    def get_route_segments(self, minimum_speed_for_segment: float = 10.0) -> np.ndarray:
        is_segment = np.zeros(self.n_gps_entries)
        is_segment[self.speed > minimum_speed_for_segment] = 1
        latest_id = 0
        segment_id = np.zeros(self.n_gps_entries)
        for i in range(self.n_gps_entries):
            if is_segment[i]:
                if i == 0 or not is_segment[i - 1]:
                    latest_id += 1
                segment_id[i] = latest_id
        return segment_id

    def read_gpx(self) -> np.ndarray:
        with open(self.file) as f:
            lines = f.readlines()
            n_segments = " ".join(lines).count("</trkpt>")
            route_array = np.zeros([n_segments, 4])
            segment_counter = 0
            for line in lines:
                stripped_line = line.strip()
                if stripped_line.startswith("<trkpt"):
                    split_line = line.split("=")
                    route_array[segment_counter, 0] = split_line[1][1:-5]  # latitude
                    route_array[segment_counter, 1] = split_line[2][1:-3]  # longitude
                elif stripped_line.startswith("<ele>"):
                    route_array[segment_counter, 2] = stripped_line.strip(
                        "<ele>"
                    ).strip("</ele>")  # altitude
                elif stripped_line.startswith("<time>"):
                    time_string = stripped_line.strip("<time>").strip("</time>")
                    try:
                        time = datetime.strptime(time_string, "%Y-%m-%dT%H:%M:%SZ")
                    except ValueError:
                        time = datetime.strptime(time_string, "%Y-%m-%dT%H:%M:%S.%fZ")
                    if segment_counter == 0:
                        start_time = time
                    route_array[segment_counter, 3] = (
                        time - start_time
                    ).total_seconds()  # seconds since first segment
                elif stripped_line.startswith("</trkpt>"):
                    segment_counter = segment_counter + 1
                else:
                    continue
        return route_array

    def __getitem__(self, key: slice) -> "Route":
        new_route = Route()
        new_route.file = self.file
        new_route.latitude = self.latitude[key]
        new_route.longitude = self.longitude[key]
        new_route.altitude = self.altitude[key]
        new_route.time = self.time[key]
        new_route.length = self.length[key]
        new_route.speed = self.speed[key]
        new_route.elevation_gain = self.elevation_gain[key]
        new_route.full_route = self.full_route
        new_route.max_index = len(new_route.latitude)
        new_route.avg_timestep = self.avg_timestep
        new_route.color = self.color
        new_route.display_name = self.display_name
        new_route.frame_step = self.frame_step
        return new_route

    def __len__(self) -> int:
        return len(self.latitude)

    def set_color(self, color: str) -> None:
        self.color = color

    def set_display_name(self, display_name: str) -> None:
        self.display_name = display_name

    def compress(self, factor=0):
        if factor==0:
            factor=10
        for attr in [
            "latitude",
            "longitude",
            "altitude",
            "length_segments",
            "time_intervals",
            "speed",
            "avg_speed",
            "route_segment_id",
            "time",
            "length",
            "elevation_gain",
        ]:
            setattr(
                self,
                attr,
                getattr(self, attr)[::factor]
            )
        self.n_gps_entries = len(self.latitude)
        self.max_index = self.n_gps_entries
        self.time_intervals = self.get_time_intervals()
        self.length_segments = self.get_length_segments()
        self.avg_timestep = np.median(self.time_intervals)
        self.frame_step = self.frame_step


def add_routes(route1: Route, route2: Route) -> Route:
    new_route = Route()
    for attr in [
        "latitude",
        "longitude",
        "altitude",
        "length_segments",
        "time_intervals",
        "speed",
        "avg_speed",
        "route_segment_id",
    ]:
        setattr(
            new_route,
            attr,
            np.concatenate((getattr(route1, attr), getattr(route2, attr))),
        )
    for attr in ["time", "length", "elevation_gain"]:
        setattr(
            new_route,
            attr,
            np.concatenate(
                (
                    getattr(route1, attr),
                    getattr(route1, attr)[-1] + getattr(route2, attr),
                )
            ),
        )
    for attr in ["n_gps_entries", "max_index"]:
        setattr(new_route, attr, getattr(route1, attr) + getattr(route2, attr))
    return new_route
