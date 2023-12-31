import numpy as np
from datetime import datetime


class Route:
    def __init__(self, file):
        self.file = file
        if file.endswith(".gpx"):
            route_array = self.read_gpx()
        else:
            print("Only .gpx files are currently supported")
        self.latitude = route_array[:, 0]
        self.longitude = route_array[:, 1]
        self.altitude = route_array[:, 2]
        self.time = route_array[:, 3]
        self.n_gps_entries = len(self.latitude)
        self._length_segments = self.get_length_segments()
        self.length = self.get_length()
        self._time_intervals = self.get_time_intervals()
        self.speed = self.get_speed()
        self.avg_speed = self.get_avg_speed()
        self.elevation_gain = self.get_elevation_gain()
        self.max_index = len(self.latitude)
        self.route_segment_id = self.get_route_segments()

    def get_length_segments(self):
        lat_to_km = 110.574
        lon_to_km = 111.320 * np.cos(self.latitude[1:]*np.pi/180.)
        length_array = np.zeros(self.n_gps_entries)
        length_array[1:] = np.sqrt(
            (lat_to_km*(self.latitude[1:] - self.latitude[:-1])) ** 2 + (lon_to_km*(self.longitude[1:] - self.longitude[:-1])) ** 2)
        return length_array #in km

    def get_elevation_gain(self):
        elev_array = np.zeros(self.n_gps_entries)
        elev_array[1:] = self.altitude[1:] - self.altitude[:-1]
        return np.cumsum(np.clip(elev_array, 0., None)) #in m

    def get_length(self):
        return np.cumsum(self._length_segments) #in km

    def get_time_intervals(self):
        time_array = np.zeros(self.n_gps_entries)
        time_array[1:] = self.time[1:] - self.time[:-1]
        return time_array

    def get_avg_speed(self):
        return np.nan_to_num(self.length/(self.time/3600.)) #in km/h

    def get_speed(self):
        return np.nan_to_num(self._length_segments/(self._time_intervals/3600.)) #in km/h

    def get_route_segments(self, minimum_speed_for_segment=10.):
        is_segment = np.zeros(self.n_gps_entries)
        is_segment[self.speed > minimum_speed_for_segment] = 1
        latest_id = 0
        segment_id = np.zeros(self.n_gps_entries)
        for i in range(self.n_gps_entries):
            if is_segment[i]:
                if i==0 or not is_segment[i-1]:
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

    def __getitem__(self, key):
        return SubRoute(self, key)


class SubRoute:
    def __init__(self, route, route_slice):
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
        if isinstance(route, SubRoute):
            self.full_route = route.full_route
        self.max_index = len(self.latitude)

    def __getitem__(self, key):
        return SubRoute(self, key)
