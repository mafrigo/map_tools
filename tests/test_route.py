from map_tools.route import *
import unittest

route = Route("../route_files/Erding_Whirlpool.gpx")
route2 = Route("../route_files/Garching_Seefeld.gpx")


class TestRouteOperations(unittest.TestCase):
    def test_route_attributes(self):
        self.assertEqual(len(route), len(route.latitude))
        self.assertEqual(len(route), len(route.longitude))

    def test_route_joining(self):
        self.assertEqual(len(route + route2), len(route)+len(route2))

    def test_subroute(self):
        self.assertEqual(isinstance(route[0:10], SubRoute), True)
        self.assertEqual(route[0:10].full_route, route)


if __name__ == '__main__':
    unittest.main()
