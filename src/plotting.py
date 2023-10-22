import numpy as np
import matplotlib.pyplot as plt
from src.route_reader import *
import math
import urllib.request as urllib2
import io
from PIL import Image



def deg2num(lat_deg, lon_deg, zoom):
  lat_rad = math.radians(lat_deg)
  n = 2.0 ** zoom
  xtile = int((lon_deg + 180.0) / 360.0 * n)
  ytile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
  return (xtile, ytile)

def num2deg(xtile, ytile, zoom):
  n = 2.0 ** zoom
  lon_deg = xtile / n * 360.0 - 180.0
  lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
  lat_deg = math.degrees(lat_rad)
  return (lat_deg, lon_deg)



def getImageCluster(lat_deg, lon_deg, delta_lat,  delta_long, zoom):
    smurl = r"https://a.tile.openstreetmap.org/{0}/{1}/{2}.png"
    xmin, ymax =deg2num(lat_deg, lon_deg, zoom)
    xmax, ymin =deg2num(lat_deg + delta_lat, lon_deg + delta_long, zoom)

    Cluster = Image.new('RGB',((xmax-xmin+1)*256-1,(ymax-ymin+1)*256-1) )
    for xtile in range(xmin, xmax+1):
        for ytile in range(ymin,  ymax+1):
            try:
                imgurl=smurl.format(zoom, xtile, ytile)
                print("Opening: " + imgurl)
                imgstr = urllib2.urlopen(imgurl).read()
                tile = Image.open(io.StringIO(imgstr))
                Cluster.paste(tile, box=((xtile-xmin)*256 ,  (ytile-ymin)*255))
            except KeyError:
                print("Couldn't download image")
                tile = None

    return Cluster


print("running")
route = Route("../test/Erding_Whirlpool.gpx")
fix, (ax0, ax1) = plt.subplots(2, 1, height_ratios=[3, 1])
ax0.plot(route.longitude, route.latitude)
ax0.set_ylabel("latitude")
ax0.set_xlabel("longitude")
ax0.axes.set_aspect('equal')
a = getImageCluster(38.5, -77.04, 0.02,  0.05, 13)
plt.imshow(np.asarray(a))
ax1.plot(route.length, route.altitude)
ax1.set_ylabel("elevation (m)")
ax1.set_xlabel("distance (km)")
#plt.plot(route.length, route.speed)
plt.tight_layout()
plt.show()