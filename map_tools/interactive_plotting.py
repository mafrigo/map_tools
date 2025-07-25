import numpy as np
from bokeh.plotting import figure, save, output_file
from bokeh.models import ColumnDataSource, HoverTool
import math
from .route import Route
from .plotting import get_frame_extent

def wgs84_to_web_mercator(lon: np.ndarray, lat: np.ndarray) -> tuple:
    """Convert WGS84 coordinates to Web Mercator"""
    k = 6378137
    x = lon * (k * math.pi/180.0)
    y = np.log(np.tan((90 + lat) * math.pi/360.0)) * k
    return x, y

def plot_interactive_route(route: Route, output_filename: str = "interactive_map.html") -> None:
    """
    Plot a Route object on an interactive Bokeh map
    
    Args:
        route: Route object containing GPS data
        output_filename: Name for output HTML file
    """
    # Convert coordinates to Web Mercator
    x, y = wgs84_to_web_mercator(np.array(route.longitude), np.array(route.latitude))
    
    # Calculate plot boundaries with 10% padding
    x_range = (min(x) - 0.1*(max(x)-min(x)), max(x) + 0.1*(max(x)-min(x)))
    y_range = (min(y) - 0.1*(max(y)-min(y)), max(y) + 0.1*(max(y)-min(y)))
    
    # Create Bokeh data source
    source = ColumnDataSource(data={
        'x': x,
        'y': y,
        'lat': route.latitude,
        'lon': route.longitude,
        'alt': route.altitude,
        'speed': route.speed
    })
    
    # Set up Bokeh figure
    p = figure(
        title=route.display_name or "Route Map",
        x_range=(min(x), max(x)),
        y_range=(min(y), max(y)),
        x_axis_type="mercator",
        y_axis_type="mercator",
        tools="pan,wheel_zoom,box_zoom,reset,save",
        active_scroll="wheel_zoom"
    )
    
    # Add OSM tiles
    p.add_tile("OSM")
    
    # Plot route
    route_line = p.line(
        'x', 'y', 
        source=source,
        line_color=route.color,
        line_width=2
    )
    
    # Add hover tool
    hover = HoverTool(
        renderers=[route_line],
        tooltips=[
            ("Position", "@lat{0.00°}, @lon{0.00°}"),
            ("Altitude", "@alt{0} m"),
            ("Speed", "@speed{0.0} km/h")
        ]
    )
    p.add_tools(hover)
    
    # Configure output
    output_file("output/"+output_filename)
    save(p)