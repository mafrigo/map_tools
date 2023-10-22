from src.plotting import make_plot, make_movie
from src.route_reader import Route

route = Route("test/Erding_Whirlpool.gpx")
make_plot(route, zoomout_fac=0.8, add_cities_in_map=True, add_real_map=False)
make_movie("test/Morning_Ride.gpx", zoomout_fac=0.8, add_cities_in_map=True, add_real_map=False)
