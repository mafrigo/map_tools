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
        self._segments = self.get_segments()
        self.length = self.get_length()
        self._time_intervals = self.get_time_intervals()
        self.speed = self.get_speed()
        self.avg_speed = self.get_avg_speed()
        self.max_index = len(self.latitude)

    def get_segments(self):
        lat_to_km = 110.574
        lon_to_km = 111.320 * np.cos(self.latitude[1:]*np.pi/180.)
        length_array = np.zeros(len(self.latitude))
        length_array[1:] = np.sqrt(
            (lat_to_km*(self.latitude[1:] - self.latitude[:-1])) ** 2 + (lon_to_km*(self.longitude[1:] - self.longitude[:-1])) ** 2)
        return length_array #in km

    def get_length(self):
        return np.cumsum(self._segments) #in km

    def get_time_intervals(self):
        time_array = np.zeros(len(self.latitude))
        time_array[1:] = self.time[1:] - self.time[:-1]
        return time_array

    def get_avg_speed(self):
        return self.length/(self.time/3600.) #in km/h

    def get_speed(self):
        return self._segments/(self._time_intervals/3600.) #in km/h

    def read_gpx(self):
        with open(self.file) as f:
            lines = f.readlines()
            n_segments = " ".join(lines).count("</trkpt>")
            route_array = np.zeros([n_segments, 4])
            #print(route_array.shape)
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


class SubRoute:
    def __init__(self, route, max_index):
        self.file = route.file
        self.latitude = route.latitude[:max_index]
        self.longitude = route.longitude[:max_index]
        self.altitude = route.altitude[:max_index]
        self.time = route.time[:max_index]
        self.length = route.length[:max_index]
        self.speed = route.speed[:max_index]
        self.full_route = route
        self.max_index = max_index
