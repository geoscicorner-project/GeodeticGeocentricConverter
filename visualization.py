# -*- coding: utf-8 -*-
"""Two-panel 2D geodetic coordinate projection diagram for QGIS."""
import math
from qgis.PyQt.QtCore import QByteArray, Qt
from qgis.PyQt.QtSvg import QSvgWidget
from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout, QSizePolicy


class CoordinateSketch(QWidget):
    """Render equatorial and meridian plane projections as a responsive SVG."""

    def __init__(self, parent=None):
        super(CoordinateSketch, self).__init__(parent)
        # Ignore the intrinsic SVG size hint: it is artwork, not a layout
        # constraint.  The parent dialog is sized from the available screen.
        # The drawing must participate in the parent layout.  Ignored/zero
        # vertical sizing caused the SVG area to collapse to almost zero.
        self.setMinimumSize(320, 260)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.view = QSvgWidget(self)
        self.view.setMinimumSize(0, 0)
        self.view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.view, 1)
        self.update_values(-6.2, 106.8, 25.0, 0.0, 0.0, 0.0,
                           6378137.0, 6356752.314245)

    @staticmethod
    def _fmt(value, digits=3):
        return format(float(value), ',.' + str(digits) + 'f')

    def update_values(self, lat, lon, h, x, y, z, a, b, flattening_exaggeration=None):
        # flattening_exaggeration is accepted for backward compatibility with 0.8.x.
        self.lat = float(lat)
        self.lon = float(lon)
        self.height = float(h)
        self.x, self.y, self.z = float(x), float(y), float(z)
        self.a, self.b = float(a), float(b)
        self._render()

    def _render(self):
        a, b = self.a, self.b
        lat = math.radians(self.lat)
        lon = math.radians(self.lon)
        sl, cl = math.sin(lat), math.cos(lat)
        e2 = 1.0 - (b * b) / (a * a)
        n = a / math.sqrt(1.0 - e2 * sl * sl)

        # Exact points in the meridian plane. The meridian diagram uses rho >= 0.
        rho_p = math.hypot(self.x, self.y)
        z_p = self.z
        rho_0 = n * cl
        z_0 = n * (1.0 - e2) * sl
        qn_z = -e2 * n * sl
        qn_offset = abs(qn_z)
        lam = math.degrees(math.atan2(self.y, self.x))

        W, H = 1440, 900
        out = [
            '<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="900" viewBox="0 0 1440 900">',
            '<rect x="0" y="0" width="1440" height="900" fill="#ffffff"/>',
            '<defs>',
            '<marker id="arrow" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto-start-reverse"><path d="M0,0 L8,4 L0,8 z" fill="#454545"/></marker>',
            '<marker id="arrowBlue" markerWidth="7" markerHeight="7" refX="4" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7 z" fill="#4b82bd"/></marker>',
            '<marker id="arrowRed" markerWidth="7" markerHeight="7" refX="4" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7 z" fill="#ad513b"/></marker>',
            '</defs>',
            '<style>text{font-family:Arial,sans-serif}.title{font-size:25px;font-weight:bold;fill:#202b38}.subtitle{font-size:24px;font-weight:bold;fill:#202b38}.axis{stroke:#111;stroke-width:2}.dim{stroke:#555;stroke-width:1.3;fill:none;marker-start:url(#arrow);marker-end:url(#arrow)}.small{font-size:13px;fill:#4b5563}.label{font-size:15px;font-weight:bold}.axislabel{font-size:20px;font-weight:bold;fill:#111}</style>',
            '<text x="355" y="82" text-anchor="middle" font-family="Arial,sans-serif" font-size="24" font-weight="bold" fill="#202b38">Equatorial Plane Projection</text>',
            '<text x="1080" y="82" text-anchor="middle" font-family="Arial,sans-serif" font-size="24" font-weight="bold" fill="#202b38">Meridian Plane Projection</text>',
            '<line x1="710" y1="100" x2="710" y2="760" stroke="#d8dde4" stroke-width="1.2"/>',
        ]

        # -------------------- LEFT: EQUATORIAL PLANE --------------------
        cx, cy, r = 355.0, 420.0, 218.0
        scale = r / a
        px, py = cx + self.x * scale, cy - self.y * scale
        axis_r = r * 1.28
        out += [
            '<circle cx="%.2f" cy="%.2f" r="%.2f" fill="#f6f3df" fill-opacity="0.78" stroke="#aeb7c3" stroke-width="2.5"/>' % (cx, cy, r),
            '<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" class="axis"/>' % (cx-axis_r, cy, cx+axis_r, cy),
            '<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" class="axis"/>' % (cx, cy+axis_r, cx, cy-axis_r),
            '<text x="%.2f" y="%.2f" font-size="20" font-weight="bold" fill="#111" text-anchor="end">X(−)</text>' % (cx-axis_r-10, cy+5),
            '<text x="%.2f" y="%.2f" font-size="20" font-weight="bold" fill="#111">X(+)</text>' % (cx+axis_r+10, cy+5),
            '<text x="%.2f" y="%.2f" font-size="20" font-weight="bold" fill="#111" text-anchor="middle">Y(+)</text>' % (cx, cy-axis_r-14),
            '<text x="%.2f" y="%.2f" font-size="20" font-weight="bold" fill="#111" text-anchor="middle">Y(−)</text>' % (cx, cy+axis_r+23),
        ]

        # Projected point and its coordinate components on X and Y axes.
        out += [
            '<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="#b0523b" stroke-width="2.3"/>' % (cx, cy, px, py),
            '<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="#4b82bd" stroke-width="2" stroke-dasharray="7 5"/>' % (px, py, px, cy),
            '<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="#4b9679" stroke-width="2" stroke-dasharray="7 5"/>' % (px, py, cx, py),
            '<circle cx="%.2f" cy="%.2f" r="6" fill="#ad513b"/>' % (px, py),
            '<circle cx="%.2f" cy="%.2f" r="5" fill="#4b82bd"/>' % (px, cy),
            '<circle cx="%.2f" cy="%.2f" r="5" fill="#4b9679"/>' % (cx, py),
            '<text x="%.2f" y="%.2f" class="label" fill="#ad513b">P_eq</text>' % (px+10, py-9),
            '<text x="%.2f" y="%.2f" font-family="Arial,sans-serif" font-size="17" font-weight="bold" fill="#4b82bd" text-anchor="middle">x(p)</text>' % (px, cy+25),
            '<text x="%.2f" y="%.2f" font-family="Arial,sans-serif" font-size="17" font-weight="bold" fill="#4b9679">y(p)</text>' % (cx+10, py+5),
        ]

        # Longitude angle lambda, measured counter-clockwise from X(+).
        angle = math.atan2(self.y, self.x)
        arc_r = 48.0
        arc_pts = []
        for i in range(41):
            t = angle * i / 40.0
            arc_pts.append((cx + arc_r * math.cos(t), cy - arc_r * math.sin(t)))
        arc_d = 'M ' + ' L '.join('%.2f %.2f' % p for p in arc_pts)
        amid = angle / 2.0
        out += [
            '<path d="%s" fill="none" stroke="#c08a2c" stroke-width="2.5"/>' % arc_d,
            '<text x="%.2f" y="%.2f" font-size="19" font-style="italic" font-weight="bold" fill="#b87916">λ</text>' % (cx+arc_r*1.22*math.cos(amid), cy-arc_r*1.22*math.sin(amid)),
            '<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" class="dim"/>' % (cx, cy+r+36, cx+r, cy+r+36),
            '<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="#777" stroke-dasharray="3 3"/>' % (cx, cy+5, cx, cy+r+40),
            '<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="#777" stroke-dasharray="3 3"/>' % (cx+r, cy, cx+r, cy+r+40),
            '<text x="%.2f" y="%.2f" text-anchor="middle" font-size="15" font-weight="bold" fill="#454545">a = %s m</text>' % (cx+r/2, cy+r+61, self._fmt(a, 0)),
        ]
        # -------------------- RIGHT: MERIDIAN PLANE --------------------
        sx, sy, sr = 1080.0, 420.0, 218.0
        def mxy(rho, zz):
            return sx + (rho / a) * sr, sy - (zz / a) * sr

        # Ellipse uses the true a:b ratio (no visual flattening exaggeration).
        out += [
            '<ellipse cx="%.2f" cy="%.2f" rx="%.2f" ry="%.2f" fill="#d7dbe1" stroke="#aeb7c3" stroke-width="2.5"/>' % (sx, sy, sr, sr*b/a),
            '<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="#c9bd65" stroke-width="1.8" stroke-dasharray="8 5"/>' % (sx-sr*1.22, sy, sx+sr*1.22, sy),
            '<text x="%.2f" y="%.2f" font-size="13" fill="#a99d42">Equatorial Plane (Z = 0)</text>' % (sx-sr*1.20, sy-9),
            '<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" class="axis"/>' % (sx, sy-sr*1.30, sx, sy+sr*1.30),
            '<text x="%.2f" y="%.2f" font-size="20" font-weight="bold" fill="#111" text-anchor="middle">Z(+)</text>' % (sx, sy-sr*1.30-12),
            '<text x="%.2f" y="%.2f" font-size="20" font-weight="bold" fill="#111" text-anchor="middle">Z(−)</text>' % (sx, sy+sr*1.30+22),
        ]

        # Semi-axes dimensions are placed to the left of the Z axis / point geometry.
        bx = sx - 34.0
        top_y = sy - sr * b / a
        out += [
            '<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" class="dim"/>' % (bx, sy, bx, top_y),
            '<text x="%.2f" y="%.2f" text-anchor="end" font-size="14" font-weight="bold" fill="#454545">b = %s m</text>' % (bx-9, (sy+top_y)/2, self._fmt(b, 0)),
        ]
        ay = sy + 31.0
        out += [
            '<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" class="dim"/>' % (sx-sr, ay, sx, ay),
            '<text x="%.2f" y="%.2f" text-anchor="middle" font-size="14" font-weight="bold" fill="#454545">a = %s m</text>' % (sx-sr/2, ay+21, self._fmt(a, 0)),
        ]

        # Qn is the actual intersection of the normal with the Z axis.
        qx, qy = mxy(0.0, qn_z)
        p0x, p0y = mxy(rho_0, z_0)
        pxm, pym = mxy(rho_p, z_p)
        ox, oy = mxy(0.0, 0.0)

        # Normal segment Qn-P is true-scale; P0 and P remain distinct.
        out += [
            '<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="#ad513b" stroke-width="2.2"/>' % (qx, qy, pxm, pym),
            '<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="#4b82bd" stroke-width="1.7"/>' % (p0x, p0y, pxm, pym),
            '<circle cx="%.2f" cy="%.2f" r="5.2" fill="#ad513b"/>' % (qx, qy),
            '<circle cx="%.2f" cy="%.2f" r="5.2" fill="#4b82bd"/>' % (p0x, p0y),
            '<circle cx="%.2f" cy="%.2f" r="6" fill="#ad513b"/>' % (pxm, pym),
            '<text x="%.2f" y="%.2f" class="small" fill="#ad513b">Qn</text>' % (qx+8, qy+18),
            '<text x="%.2f" y="%.2f" class="label" fill="#4b82bd">P₀</text>' % (p0x+9, p0y+17),
            '<text x="%.2f" y="%.2f" class="label" fill="#ad513b">P</text>' % (pxm+10, pym-8),
        ]
        # Label N+h along the actual Qn-P line.
        midx, midy = (qx+pxm)/2.0, (qy+pym)/2.0
        out.append('<text x="%.2f" y="%.2f" font-size="15" font-weight="bold" fill="#ad513b">N + h</text>' % (midx+12, midy-8))

        # Center marker and the true (usually tiny) Center-Qn offset.
        out += [
            '<circle cx="%.2f" cy="%.2f" r="3.5" fill="#222"/>' % (ox, oy),
        ]

        # Insets: intentionally schematic, not drawn to the ellipsoid's scale.
        # Upper-left: P0-P height detail.
        ix, iy, iw, ih = 735.0, 145.0, 205.0, 132.0
        out += [
            '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="4" fill="#ffffff" stroke="#9299a3" stroke-width="1.2"/>' % (ix, iy, iw, ih),
            '<text x="%.1f" y="%.1f" font-size="15" font-weight="bold" text-anchor="middle" fill="#303b49">Ellipsoidal height detail (h)</text>' % (ix+iw/2, iy+18),
            '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#4b82bd" stroke-width="2.2" marker-end="url(#arrowBlue)"/>' % (ix+40, iy+72, ix+iw-35, iy+72),
            '<circle cx="%.1f" cy="%.1f" r="5" fill="#4b82bd"/><circle cx="%.1f" cy="%.1f" r="5" fill="#ad513b"/>' % (ix+40, iy+72, ix+iw-35, iy+72),
            '<text x="%.1f" y="%.1f" font-size="12" font-weight="bold" fill="#4b82bd">P₀</text>' % (ix+31, iy+55),
            '<text x="%.1f" y="%.1f" font-size="12" font-weight="bold" fill="#ad513b">P</text>' % (ix+iw-40, iy+55),
            '<text x="%.1f" y="%.1f" text-anchor="middle" font-size="13" font-weight="bold" fill="#4b82bd">h = %s m</text>' % (ix+iw/2, iy+111, self._fmt(self.height, 3)),
        ]

        # Lower-left: Center-to-Qn offset detail. Schematic only (not to scale).
        # Qn is above Center when Qn Z is positive, and below it when negative.
        jx, jy, jw, jh = 735.0, 565.0, 205.0, 142.0
        center_detail_y = jy + 78.0
        qn_detail_y = jy + 48.0 if qn_z > 0.0 else jy + 108.0
        arrow_start_y = center_detail_y + ( -7.0 if qn_z > 0.0 else 7.0 )
        arrow_end_y = qn_detail_y + ( 7.0 if qn_z > 0.0 else -7.0 )
        out += [
            '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="4" fill="#ffffff" stroke="#9299a3" stroke-width="1.2"/>' % (jx, jy, jw, jh),
            '<text x="%.1f" y="%.1f" text-anchor="middle" font-size="13" font-weight="bold" fill="#303b49">Center–Qn offset detail</text>' % (jx+jw/2, jy+18),
            '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#b8bec7" stroke-width="1" stroke-dasharray="3 3"/>' % (jx+jw/2, jy+31, jx+jw/2, jy+jh-31),
            '<circle cx="%.1f" cy="%.1f" r="5" fill="#222"/><circle cx="%.1f" cy="%.1f" r="5" fill="#ad513b"/>' % (jx+jw/2, center_detail_y, jx+jw/2, qn_detail_y),
            '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#ad513b" stroke-width="1.8" marker-end="url(#arrowRed)"/>' % (jx+jw/2, arrow_start_y, jx+jw/2, arrow_end_y),
            '<text x="%.1f" y="%.1f" font-size="12" fill="#303b49">Center</text>' % (jx+jw/2+12, center_detail_y+4),
            '<text x="%.1f" y="%.1f" font-size="12" font-weight="bold" fill="#ad513b">Qn</text>' % (jx+jw/2+12, qn_detail_y+4),
            '<text x="%.1f" y="%.1f" text-anchor="middle" font-size="12" font-weight="bold" fill="#ad513b">Qn Z = %s m</text>' % (jx+jw/2, jy+132, self._fmt(qn_z, 3)),
        ]

        # Compact one-line coordinate footer.
        footer = (
            'Geodetic: B = %.6f°  L = %.6f°  h = %s m   |   '
            'ECEF: X = %s  Y = %s  Z = %s m   |   '
            'N = %s m  Qn Z = %s m  λ = %.6f°'
        ) % (
            self.lat, self.lon, self._fmt(self.height, 3),
            self._fmt(self.x, 3), self._fmt(self.y, 3), self._fmt(self.z, 3),
            self._fmt(n, 3), self._fmt(qn_z, 3), lam
        )
        out += [
            '<text x="720" y="850" text-anchor="middle" font-family="Arial,sans-serif" font-size="15" fill="#344054">%s</text>' % footer,
            '</svg>'
        ]
        self.view.load(QByteArray(''.join(out).encode('utf-8')))
        self.view.renderer().setAspectRatioMode(Qt.KeepAspectRatio)
