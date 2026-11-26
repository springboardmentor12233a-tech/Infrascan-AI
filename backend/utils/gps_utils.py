import sys, os
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

def get_exif_data(image_path: str):
    try:
        image = Image.open(image_path)
        exif_data = {}
        info = image._getexif()
        if not info:
            return None
        for tag, value in info.items():
            decoded = TAGS.get(tag, tag)
            if decoded == "GPSInfo":
                gps_data = {}
                for t in value:
                    sub_decoded = GPSTAGS.get(t, t)
                    gps_data[sub_decoded] = value[t]
                exif_data[decoded] = gps_data
            else:
                exif_data[decoded] = value
        return exif_data
    except Exception:
        return None

def _convert_to_degrees(value):
    d = float(value[0])
    m = float(value[1])
    s = float(value[2])
    return d + (m / 60.0) + (s / 3600.0)

def extract_gps_coordinates(image_path: str):
    """Extracts latitude and longitude from EXIF metadata. Returns (lat, lon) or None."""
    exif = get_exif_data(image_path)
    if not exif or "GPSInfo" not in exif:
        return None
    gps_info = exif["GPSInfo"]
    try:
        lat_ref = gps_info.get("GPSLatitudeRef")
        lat = gps_info.get("GPSLatitude")
        lon_ref = gps_info.get("GPSLongitudeRef")
        lon = gps_info.get("GPSLongitude")

        if lat and lon and lat_ref and lon_ref:
            latitude = _convert_to_degrees(lat)
            if lat_ref != "N":
                latitude = -latitude

            longitude = _convert_to_degrees(lon)
            if lon_ref != "E":
                longitude = -longitude

            return round(latitude, 6), round(longitude, 6)
    except Exception:
        pass
    return None
