from src.plotting import make_plot
from src.route_reader import Route

route = Route("test/Erding_Whirlpool.gpx")
make_plot(route, add_cities_in_map=True, add_real_map=False)
