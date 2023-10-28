from src.plotting import plot_route_on_map, plot_route_on_graph, make_movie
from src.route_reader import Route

#route = Route("route_files/Erding_Whirlpool.gpx")
#route = Route("route_files/Morning_Ride.gpx")
route = Route("route_files/Munich_Budapest.gpx")
plot_route_on_map(route, zoomout_fac=0.2, output_file="map")
plot_route_on_graph(route, zoomout_fac=0.2, output_file="graph")
#make_movie(route, zoomout_fac=0.2, frame_step=20, output_file="movie")
make_movie(route, zoomout_fac=0.2, frame_step=5, output_file="movie", delta_if_centered=0.1)#, cut_at_frame=300)
