from map_tools.plotting import *
import unittest

route = Route("../route_files/Erding_Whirlpool.gpx")


class TestMapPlot(unittest.TestCase):

    def test_zoom_level(self):
        self.assertEqual(isinstance(get_zoom_level(1), int), True)

    def test_frame_extent(self):
        frame_extent = get_frame_extent(route)
        self.assertLess(frame_extent[0], np.min(route.longitude))
        self.assertGreater(frame_extent[1], np.max(route.longitude))
        self.assertLess(frame_extent[2], np.min(route.latitude))
        self.assertGreater(frame_extent[3], np.max(route.latitude))

    def test_background_map(self):
        ax = create_background_map([11.6, 12.0, 48.2, 48.4])
        self.assertEqual(isinstance(ax, plt.Axes), True)


if __name__ == '__main__':
    unittest.main()
