import numpy as np
from bokeh.plotting import figure, save, output_file
from bokeh.models import ColumnDataSource, HoverTool, Slider, CustomJS, Div
from bokeh.layouts import column, row
import math
from .route import Route

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
    
    # Create Bokeh data source with additional metrics
    source = ColumnDataSource(data={
        'x': x,
        'y': y,
        'lat': route.latitude,
        'lon': route.longitude,
        'alt': route.altitude,
        'speed': route.speed,
        'length': route.length,
        'time': route.time,
        'avg_speed': route.avg_speed,
        'elevation_gain': route.elevation_gain
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
    
    # Create current position marker source
    current_source = ColumnDataSource(data={
        'x': [x[0]],
        'y': [y[0]],
        'lat': [route.latitude[0]],
        'lon': [route.longitude[0]],
        'alt': [route.altitude[0]],
        'speed': [route.speed[0]]
    })
    
    # Add current position marker
    position_marker = p.circle(
        'x', 'y',
        source=current_source,
        size=10,
        color='red',
        alpha=0.8
    )
    
    # Create metric displays
    time_display = Div(text="<b>Time:</b> 0h 0m", styles={'font-size': '12pt'})
    distance_display = Div(text="<b>Distance:</b> 0.00 km", styles={'font-size': '12pt'})
    elevation_display = Div(text="<b>Elevation Gain:</b> 0 m", styles={'font-size': '12pt'})
    speed_display = Div(text="<b>Speed:</b> 0.0 km/h", styles={'font-size': '12pt'})
    
    # Create slider
    slider = Slider(
        start=0,
        end=len(x)-1,
        value=0,
        step=1,
        title="Position Index"
    )
    
    # Create metrics row
    metrics_row = row(
        time_display,
        distance_display,
        elevation_display,
        speed_display,
        sizing_mode="stretch_width"
    )
    
    # JavaScript callback for slider with additional metrics and display updates
    slider.js_on_change('value', CustomJS(args={
        'source': source,
        'current_source': current_source,
        'time_display': time_display,
        'distance_display': distance_display,
        'elevation_display': elevation_display,
        'speed_display': speed_display
    }, code="""
        const index = cb_obj.value;
        const time = source.data.time[index];
        const hours = Math.floor(time / 3600);
        const minutes = Math.floor((time % 3600) / 60);
        
        current_source.data = {
            x: [source.data.x[index]],
            y: [source.data.y[index]],
            lat: [source.data.lat[index]],
            lon: [source.data.lon[index]],
            alt: [source.data.alt[index]],
            speed: [source.data.speed[index]],
            length: [source.data.length[index]],
            time: [source.data.time[index]],
            avg_speed: [source.data.avg_speed[index]],
            elevation_gain: [source.data.elevation_gain[index]]
        };
        
        time_display.text = `<b>Time:</b> ${hours}h ${minutes}m`;
        distance_display.text = `<b>Distance:</b> ${source.data.length[index].toFixed(2)} km`;
        elevation_display.text = `<b>Elevation Gain:</b> ${Math.round(source.data.elevation_gain[index])} m`;
        speed_display.text = `<b>Speed:</b> ${source.data.speed[index].toFixed(1)} km/h`;
        
        current_source.change.emit();
    """))
    
    # Combine plot, metrics and slider with proper sizing
    layout = column(
        p,
        metrics_row,
        slider,
        sizing_mode="stretch_width"
    )
    
    # Configure output
    output_file("output/"+output_filename)
    save(layout)