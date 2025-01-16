mime_to_extension = {
    "image/tiff": ".tif",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/bmp": ".bmp",
    "image/webp": ".webp",
    "application/zip": ".zip",
    "application/x-rar-compressed": ".rar",
    "application/x-7z-compressed": ".7z",
    "application/gzip": ".gz",
    "application/x-tar": ".tar",
    "text/csv": ".csv",
    "text/plain": ".txt",
    "application/json": ".json",
    "application/xml": ".xml",
    "application/gpx+xml": ".gpx",
    "application/vnd.google-earth.kml+xml": ".kml",
    "application/vnd.google-earth.kmz": ".kmz",
    "application/gml+xml": ".gml",
    "application/geopackage+sqlite3": ".gpkg",
    "application/x-esri-shape": ".shp",
    "application/x-qgis": ".qgs",
    "application/x-qgis-project": ".qgz",
    "application/x-mapinfo-mif": ".mif",
    "application/x-mapinfo-mid": ".mid",
    "application/octet-stream": ".bin",
    "application/x-sqlite3": ".sqlite",
    "application/vnd.sqlite3": ".db",
    "application/x-dbase": ".dbf",
    "application/x-dwg": ".dwg",
    "application/x-dxf": ".dxf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.oasis.opendocument.text": ".odt",
    "application/vnd.oasis.opendocument.spreadsheet": ".ods",
    "application/vnd.oasis.opendocument.presentation": ".odp",
    "application/pdf": ".pdf",
    "text/html": ".html",
    "text/css": ".css",
    "application/javascript": ".js",
    "audio/mpeg": ".mp3",
    "video/mp4": ".mp4",
    "application/x-netcdf": ".nc",
    "application/x-hdf": ".hdf",
}


def get_extension_from_mime(mime_type: str) -> str:
    """Get the appropriate file extension for a given MIME type.

    Args:
        mime_type (str): The MIME type of the file.

    Returns:
        str: The corresponding file extension (including the dot) or
            an empty string if not found.
    """
    return mime_to_extension.get(mime_type, "")
