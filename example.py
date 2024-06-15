from map_tools.route import Route
from map_tools.plotting import plot_single_route, plot_multiple_routes
from map_tools.movie import make_movie_with_dynamic_map, make_movie_with_static_map, make_movie_with_multiple_routes
import time

t0 = time.time()
route = Route("route_files/Erding_Whirlpool.gpx", color='violet', display_name='1')
route2 = Route("route_files/Bad_Toelz.gpx", color='blue', display_name='2')
route3 = Route("route_files/Munich_Prague.gpx", color='darkgreen', display_name='3')
route4 = Route("route_files/Munich_Budapest.gpx", color='k', display_name='4')
route5 = Route("route_files/Garching_Seefeld.gpx", color='red', display_name='5')
route6 = Route("route_files/Morning_Ride.gpx", color='crimson', display_name='6')
route7 = Route("route_files/Ronde_van_Noord_Holland.gpx", color='red', display_name='7')

# Plot whole route on a map
plot_single_route(route7, output_file="map")

# Join two maps and plot them separating continuous ride segments with different colours
plot_single_route(route + route2, output_file="map_joined", color_segments=True)

# Plot two routes together
plot_multiple_routes([route, route2, route3, route4, route5], output_file="multiple_routes")

# Make a movie of the route on a static map - commented out because it takes a long time
#make_movie_with_static_map(route2, output_file="static_movie")

# Make a movie of the route on a zoomed-in moving map, with optional zoom-out at the end - commented out because it takes a long time
#make_movie_with_dynamic_map(route, map_frame_size_in_deg=0.1, output_file="dynamic_movie", final_zoomout=False)

# Make a movie of two routes together
make_movie_with_multiple_routes([route5, route2], frame_style='dynamic')

t1 = time.time()
print("\nFinished in %.1f seconds" % (t1 - t0))
