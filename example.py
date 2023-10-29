from map_tools.route_reader import Route
from map_tools.plotting import plot_route_on_map
from map_tools.movie import make_movie_with_dynamic_map, make_movie_with_static_map
import time


t0 = time.time()
route = Route("route_files/Ronde_van_Noord_Holland.gpx")

#Plot whole route on a map
plot_route_on_map(route, output_file="map")

#Make a movie of the route on a static map
make_movie_with_static_map(route, frame_step=10, output_file="static_movie")

#Make a movie of the route on a zoomed-in moving map, with optional zoom-out at the end
make_movie_with_dynamic_map(route, map_frame_size_in_deg=0.1, frame_step=3, output_file="dynamic_movie")

t1 = time.time()
print("\nFinished in %.1f seconds" %(t1-t0))
