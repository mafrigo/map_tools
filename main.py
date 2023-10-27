from src.plotting import plot_route_on_map, plot_route_on_graph, make_movie
from src.route_reader import Route

route = Route("route_files/Erding_Whirlpool.gpx")
#route = Route("route_files/Morning_Ride.gpx")
#route = Route("route_files/Munich_Budapest_1.gpx")
plot_route_on_map(route, zoomout_fac=0.3, output_file="map")
plot_route_on_graph(route, zoomout_fac=0.3, output_file="graph")
#make_movie(route, zoomout_fac=0.3, frame_step=50, output_file="movie")
