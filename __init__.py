# -*- coding: utf-8 -*-
def classFactory(iface):
    from .geodetic_geocentric import GeodeticGeocentricConverter
    return GeodeticGeocentricConverter(iface)
