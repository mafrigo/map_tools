from src.route_reader import Route
from src.plotting import plot_route_on_map
from src.movie import make_movie
import time


t0 = time.time()
route = Route("route_files/Erding_Whirlpool.gpx")
#route = Route("route_files/Morning_Ride.gpx")
#route = Route("route_files/Munich_Budapest.gpx")
#route = Route("route_files/Munich_Prague.gpx")
#route = Route("route_files/Garching_Seefeld.gpx")
#route = Route("route_files/Ronde_van_Noord_Holland.gpx")

#Plot whole route on a map
plot_route_on_map(route, output_file="map")

#Make a movie of the route on a static map
#make_movie(route, frame_step=20, output_file="movie")

#Make a movie of the route on a zoomed-in moving map, with optional zoom-out at the end
make_movie(route, frame_step=3, output_file="movie", delta_if_centered=0.1)#, cut_at_frame=500)

t1 = time.time()
print("\nFinished in %.1f seconds" %(t1-t0))
