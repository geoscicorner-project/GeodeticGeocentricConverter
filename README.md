# Geodetic–Geocentric Converter

A QGIS plugin for converting coordinates between geodetic ellipsoidal form and geocentric Earth-Centered, Earth-Fixed (ECEF) Cartesian form.

**Repository:** https://github.com/geoscicorner-project/Geodetic-Geocentric-Converter

## Features

- Convert geodetic coordinates (latitude, longitude, ellipsoidal height) to geocentric Cartesian coordinates (X, Y, Z).
- Convert geocentric Cartesian coordinates (X, Y, Z) to geodetic coordinates (latitude, longitude, ellipsoidal height).
- Select an ellipsoid from the QGIS ellipsoid definitions or enter custom semi-major axis and inverse-flattening parameters.
- Enter angular coordinates in degrees, minutes, and seconds (DMS).
- View conversion results, intermediate calculation values, and coordinate quadrant/hemisphere information.
- Inspect synchronized equatorial-plane and meridian-plane diagrams, including the ellipsoid axes, longitude angle, ellipsoid normal, prime-vertical radius, ellipsoidal height, and the Center–Qn offset.
- Resize and use the dialog across multi-monitor desktop configurations.

## Coordinate model

For geodetic latitude B, longitude L, ellipsoidal height h, semi-major axis a, and first eccentricity squared e²:

```text
e² = 1 - b²/a²
N  = a / sqrt(1 - e² sin²(B))
X  = (N+h) cos(B) cos(L)
Y  = (N+h) cos(B) sin(L)
Z  = (N(1-e²)+h) sin(B)
```

The ellipsoid surface point is:

```text
P₀ = (N cos(B) cos(L), N cos(B) sin(L), N(1-e²) sin(B))
```

The ellipsoid normal intersects the Z axis at:

```text
Qₙ = (0, 0, -e² N sin(B))
```

The distance from Qₙ to P along the ellipsoid normal is N+h, while the ellipsoidal height is the segment P₀–P. Qₙ does not generally coincide with the ellipsoid centre.

## Installation

1. Open QGIS.
2. Go to **Plugins → Manage and Install Plugins → Install from ZIP**.
3. Select the plugin ZIP package.
4. Enable **Geodetic-Geocentric Converter** from the Plugins menu.

## Compatibility

- QGIS 3.16 or later.
- Uses the PyQt and QtSvg modules provided by QGIS.

## License

This project is licensed under the GNU General Public License v2.0 or (at your option) any later version. See [LICENSE](LICENSE) for the full license text.

## Maintainer

GeosciCorner Project  
https://github.com/geoscicorner-project/Geodetic-Geocentric-Converter
