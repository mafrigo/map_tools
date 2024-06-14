from map_tools.route import Route
from map_tools.plotting import plot
from map_tools.movie import make_movie_with_dynamic_map, make_movie_with_static_map
import time


t0 = time.time()
route = Route("route_files/Erding_Whirlpool.gpx")
route2 = Route("route_files/Morning_Ride.gpx")
route3 = Route("route_files/Garching_Seefeld.gpx")
route4 = Route("route_files/Munich_Prague.gpx")
route5 = Route("route_files/Munich_Budapest.gpx")

#Plot whole route on a map
plot(route+route2+route3+route4+route5, output_file="map", color_segments=False)

#Make a movie of the route on a static map
#make_movie_with_static_map(route, frame_step=10, output_file="static_movie")

#Make a movie of the route on a zoomed-in moving map, with optional zoom-out at the end
#make_movie_with_dynamic_map(route, map_frame_size_in_deg=0.1, frame_step=30, output_file="dynamic_movie")

t1 = time.time()
print("\nFinished in %.1f seconds" %(t1-t0))
