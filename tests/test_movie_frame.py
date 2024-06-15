from map_tools.movie_frame import *
from typing import List
import unittest

route = Route("../route_files/Erding_Whirlpool.gpx")
route2 = Route("../route_files/Garching_Seefeld.gpx")


class TestMovieFrame(unittest.TestCase):

    def test_dynamic_extent(self):
        extent = get_dynamic_frame_extent_for_multiple_routes([route, route2])
        self.assertEqual(isinstance(extent, List), True)
        self.assertEqual(isinstance(extent[0], float), True)

    def test_trail(self):
        trail = get_trail(route[0:20])
        self.assertEqual(isinstance(trail, LineCollection), True)


if __name__ == '__main__':
    unittest.main()
