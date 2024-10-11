from map_tools.route import Route
from map_tools.plotting import plot_single_route, plot_multiple_routes
from map_tools.movie import make_movie_with_dynamic_map, make_movie_with_static_map, make_movie_with_multiple_routes
import time

t0 = time.time()
route = Route("route_files/Erding_Whirlpool.gpx", color='violet', display_name='1')
route2 = Route("route_files/Bad_Toelz.gpx", color='blue', display_name='2')
route3 = Route("route_files/Munich_Prague.gpx", color='darkgreen')
route4 = Route("route_files/Munich_Budapest.gpx", color='red')
route5 = Route("route_files/Garching_Seefeld.gpx", color='red', display_name='5')
route7 = Route("route_files/Ronde_van_Noord_Holland.gpx", color='red', display_name='7')
route9 = Route("route_files/Super_Mario_Ebersberg.gpx", color='red', display_name='M')

# Compress big routes to speed up computation
route3.compress(factor=100)
route4.compress(factor=100)
route5.compress(factor=30)
route9.compress(factor=8)

# Plot whole route on a map
plot_single_route(route7, output_file="example_map")
plot_single_route(route9, output_file="Super_Mario_Ebersberg")

# Join two maps and plot them separating continuous ride segments with different colours
plot_single_route(route + route2, output_file="map_joined", color_segments=True)

# Plot two routes together
plot_multiple_routes([route3, route4], output_file="Prague_and_Budapest")

# Make a movie of the route on a static map - commented out because it takes a long time
make_movie_with_static_map(route9, output_file="static_movie_Mario")

# Make a movie of the route on a zoomed-in moving map, with zoom-out at the end
make_movie_with_dynamic_map(route5, map_frame_size_in_deg=0.2, final_zoomout=True, output_file="dynamic_movie_Seefeld")

# Make a movie of two routes together
make_movie_with_multiple_routes([route3, route4], dynamic_frame=True, use_real_time=True, final_zoomout=False,
                                output_file="race_movie_Budapest_Prague")

t1 = time.time()
print("\nFinished in %.1f seconds" % (t1 - t0))