# -*- coding: utf-8 -*-
"""Geodetic <-> geocentric calculations. Angles are in decimal degrees at the API."""
import math


def ellipsoid_from_a_invf(a, inv_f):
    a = float(a)
    inv_f = float(inv_f)
    if a <= 0:
        raise ValueError('Semi-major axis a must be greater than zero.')
    if inv_f <= 1:
        raise ValueError('Inverse flattening must be greater than 1 for an oblate ellipsoid.')
    f = 1.0 / inv_f
    b = a * (1.0 - f)
    e2 = f * (2.0 - f)
    return {'a': a, 'b': b, 'inv_f': inv_f, 'f': f, 'e2': e2}


def geodetic_to_geocentric(lat_deg, lon_deg, h, a, inv_f):
    """Return X,Y,Z (m), plus useful intermediate values."""
    p = ellipsoid_from_a_invf(a, inv_f)
    if not -90.0 <= float(lat_deg) <= 90.0:
        raise ValueError('Latitude must be within the range -90 to +90 degrees.')
    lat = math.radians(float(lat_deg))
    lon = math.radians(float(lon_deg))
    h = float(h)
    sin_lat, cos_lat = math.sin(lat), math.cos(lat)
    n = p['a'] / math.sqrt(1.0 - p['e2'] * sin_lat * sin_lat)
    x = (n + h) * cos_lat * math.cos(lon)
    y = (n + h) * cos_lat * math.sin(lon)
    z = (n * (1.0 - p['e2']) + h) * sin_lat
    return {'x': x, 'y': y, 'z': z, 'N': n, 'p': p}


def geocentric_to_geodetic(x, y, z, a, inv_f):
    """Bowring initial estimate followed by fixed-point refinement."""
    p = ellipsoid_from_a_invf(a, inv_f)
    x, y, z = float(x), float(y), float(z)
    aa, bb, e2 = p['a'], p['b'], p['e2']
    ep2 = (aa * aa - bb * bb) / (bb * bb)
    rho = math.hypot(x, y)
    if rho < 1e-12 and abs(z) < 1e-12:
        raise ValueError('Latitude and longitude are undefined at the ellipsoid centre.')
    if rho < 1e-12:
        lat = math.copysign(math.pi / 2.0, z)
        h = abs(z) - bb
        lon = 0.0  # longitude is mathematically undefined at the poles; convention 0°
        return {'lat': math.degrees(lat), 'lon': lon, 'h': h, 'N': aa / math.sqrt(1.0-e2), 'p': p,
                'note': 'At the poles, longitude is undefined and is displayed as 0° by convention.'}
    theta = math.atan2(z * aa, rho * bb)
    st, ct = math.sin(theta), math.cos(theta)
    lat = math.atan2(z + ep2 * bb * st**3, rho - e2 * aa * ct**3)
    # Refine latitude and height until stable.
    h = 0.0
    for _ in range(20):
        sl, cl = math.sin(lat), math.cos(lat)
        n = aa / math.sqrt(1.0 - e2 * sl * sl)
        if abs(cl) > 1e-12:
            h = rho / cl - n
        else:
            h = z / sl - n * (1.0 - e2)
        denom = rho * (1.0 - e2 * n / (n + h))
        new_lat = math.atan2(z, denom)
        if abs(new_lat - lat) < 1e-14:
            lat = new_lat
            break
        lat = new_lat
    sl, cl = math.sin(lat), math.cos(lat)
    n = aa / math.sqrt(1.0 - e2 * sl * sl)
    h = rho / cl - n if abs(cl) > 1e-10 else z / sl - n * (1.0-e2)
    lon = math.atan2(y, x)
    return {'lat': math.degrees(lat), 'lon': math.degrees(lon), 'h': h, 'N': n, 'p': p, 'note': ''}
