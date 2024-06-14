from map_tools.route import Route
from map_tools.plotting import plot, multi_plot
from map_tools.movie import make_movie_with_dynamic_map, make_movie_with_static_map
import time

t0 = time.time()
route = Route("route_files/Erding_Whirlpool.gpx")
route2 = Route("route_files/Garching_Seefeld.gpx")
route3 = Route("route_files/Morning_Ride.gpx")
route.set_color('blue')
route.set_display_name('MF')
route2.set_display_name('2')
route3.set_color('darkorange')
route3.set_display_name('<3')

# Plot whole route on a map
plot(route, output_file="map")

# Join two maps and plot them separating segments with different colours
plot(route + route2, output_file="map_joined", color_segments=True)

# Plot two routes together
multi_plot([route, route2], output_file="multiple_routes")

# Make a movie of the route on a static map - commented out because it takes a long time
#make_movie_with_static_map(route3, output_file="static_movie")

# Make a movie of the route on a zoomed-in moving map, with optional zoom-out at the end - commented out because it takes a long time
#make_movie_with_dynamic_map(route, map_frame_size_in_deg=0.1, output_file="dynamic_movie", final_zoomout=False)

t1 = time.time()
print("\nFinished in %.1f seconds" % (t1 - t0))
