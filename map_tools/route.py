import numpy as np
from datetime import datetime
from .config import get_yaml_config
cfg = get_yaml_config()


class Route(object):
    file = ""
    latitude = np.array([])
    longitude = np.array([])
    altitude = np.array([])
    time = np.array([])
    n_gps_entries = 0
    length_segments = np.array([])
    length = np.array([])
    time_intervals = np.array([])
    speed = np.array([])
    avg_speed = np.array([])
    elevation_gain = np.array([])
    max_index = 0
    route_segment_id = np.array([])
    avg_timestep = 1
    full_route = None
    color = cfg["default_route_color"]
    display_name = ''

    def __init__(self, file: str = ""):
        if len(file) > 0:
            self.route_from_file(file)
        self.full_route = self

    def route_from_file(self, file: str):
        self.file = file
        if file.endswith(".gpx"):
            route_array = self.read_gpx()
        else:
            raise IOError("Only .gpx files are currently supported")
        self.latitude = route_array[:, 0]
        self.longitude = route_array[:, 1]
        self.altitude = route_array[:, 2]
        self.time = route_array[:, 3]
        self.n_gps_entries = len(self.latitude)
        self.length_segments = self.get_length_segments()
        self.length = self.get_length()
        self.time_intervals = self.get_time_intervals()
        self.speed = self.get_speed()
        self.avg_speed = self.get_avg_speed()
        self.elevation_gain = self.get_elevation_gain()
        self.max_index = len(self.latitude)
        self.route_segment_id = self.get_route_segments()
        self.avg_timestep = np.mean(self.time_intervals)

    def __add__(self, other):
        return add_routes(self, other)

    def get_length_segments(self):
        lat_to_km = 110.574
        lon_to_km = 111.320 * np.cos(self.latitude[1:] * np.pi / 180.)
        length_array = np.zeros(self.n_gps_entries)
        length_array[1:] = np.sqrt(
            (lat_to_km * (self.latitude[1:] - self.latitude[:-1])) ** 2 + (
                    lon_to_km * (self.longitude[1:] - self.longitude[:-1])) ** 2)
        return length_array  # in km

    def get_elevation_gain(self):
        elev_array = np.zeros(self.n_gps_entries)
        elev_array[1:] = self.altitude[1:] - self.altitude[:-1]
        return np.cumsum(np.clip(elev_array, 0., None))  # in m

    def get_length(self):
        return np.cumsum(self.length_segments)  # in km

    def get_time_intervals(self):
        time_array = np.zeros(self.n_gps_entries)
        time_array[1:] = self.time[1:] - self.time[:-1]
        return time_array

    def get_avg_speed(self):
        return np.nan_to_num(self.length / (self.time / 3600.))  # in km/h

    def get_speed(self):
        return np.nan_to_num(self.length_segments / (self.time_intervals / 3600.))  # in km/h

    def get_route_segments(self, minimum_speed_for_segment: float = 10.):
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

    def read_gpx(self):
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
                    route_array[segment_counter, 2] = stripped_line.strip("<ele>").strip("</ele>")  # altitude
                elif stripped_line.startswith("<time>"):
                    time_string = stripped_line.strip("<time>").strip("</time>")
                    time = datetime.strptime(time_string, "%Y-%m-%dT%H:%M:%SZ")
                    if segment_counter == 0:
                        start_time = time
                    route_array[segment_counter, 3] = (time - start_time).total_seconds()  # seconds since first segment
                elif stripped_line.startswith("</trkpt>"):
                    segment_counter = segment_counter + 1
                else:
                    continue
        return route_array

    def __getitem__(self, key: slice):
        return SubRoute(self, key)

    def __len__(self):
        return len(self.latitude)

    def set_color(self, color: str):
        self.color = color

    def set_display_name(self, display_name: str):
        self.display_name = display_name


def add_routes(route1: Route, route2: Route) -> Route:
    new_route = Route()
    for attr in ["latitude", "longitude", "altitude", "time", "length_segments", "length",
                 "time_intervals", "speed", "avg_speed", "elevation_gain", "route_segment_id"]:
        setattr(new_route, attr, np.concatenate((getattr(route1, attr), getattr(route2, attr))))
    for attr in ["n_gps_entries", "max_index"]:
        setattr(new_route, attr, getattr(route1, attr) + getattr(route2, attr))
    return new_route


class SubRoute:
    def __init__(self, route, route_slice: slice):
        self.file = route.file
        self.latitude = route.latitude[route_slice]
        self.longitude = route.longitude[route_slice]
        self.altitude = route.altitude[route_slice]
        self.time = route.time[route_slice]
        self.length = route.length[route_slice]
        self.speed = route.speed[route_slice]
        self.elevation_gain = route.elevation_gain[route_slice]
        if isinstance(route, Route):
            self.full_route = route
        elif isinstance(route, SubRoute):
            self.full_route = route.full_route
        else:
            raise IOError("route must be either a Route or a Subroute object")
        self.max_index = len(self.latitude)
        self.avg_timestep = route.avg_timestep
        self.color = route.color
        self.display_name = route.display_name

    def __getitem__(self, key: slice):
        return SubRoute(self, key)
