# -*- coding: utf-8 -*-
import math
import os
from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtGui import QGuiApplication, QIcon
from qgis.PyQt.QtWidgets import (QAction, QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QComboBox, QDoubleSpinBox, QPushButton, QGroupBox, QTabWidget, QWidget,
    QGridLayout, QMessageBox, QLineEdit, QPlainTextEdit, QCheckBox, QSpinBox, QSizePolicy, QScrollArea, QSplitter)
from qgis.core import QgsProject, QgsEllipsoidUtils
from .coordinate_math import ellipsoid_from_a_invf, geodetic_to_geocentric, geocentric_to_geodetic
from .visualization import CoordinateSketch


class GeodeticGeocentricConverter:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None

    def initGui(self):
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.svg')
        self.action = QAction(QIcon(icon_path), 'Geodetic-Geocentric Converter', self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu('&Geodetic-Geocentric Converter', self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        if self.action:
            self.iface.removePluginMenu('&Geodetic-Geocentric Converter', self.action)
            self.iface.removeToolBarIcon(self.action)

    def run(self):
        if self.dialog is None:
            self.dialog = ConverterDialog(self.iface.mainWindow())
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()


class ConverterDialog(QDialog):
    def __init__(self, parent=None):
        super(ConverterDialog, self).__init__(parent)
        self.setWindowTitle('Geodetic–Geocentric Converter')
        # Choose a sensible initial size for the screen where QGIS is running.
        # After opening, let the user resize freely. Moving the dialog between
        # monitors must not trigger an unsolicited resize or recenter operation.
        self._initial_screen_fit_done = False
        self._tracked_screen = None
        self._screen_signal_connected = False
        self.setMinimumSize(760, 520)
        self.setSizeGripEnabled(True)
        self._build_ui()
        self._load_ellipsoids()
        self._calculate()

    def _screen_for_dialog(self):
        """Return the screen currently containing this dialog or its parent."""
        handle = self.windowHandle()
        if handle is not None:
            screen = handle.screen()
            if screen is not None:
                return screen

        parent = self.parentWidget()
        if parent is not None:
            screen = QGuiApplication.screenAt(parent.frameGeometry().center())
            if screen is not None:
                return screen

        screen = self.screen()
        if screen is not None:
            return screen
        return QGuiApplication.primaryScreen()

    def _fit_initial_to_available_screen(self):
        if self._initial_screen_fit_done:
            return
        screen = self._screen_for_dialog()
        if screen is None:
            self.resize(1200, 800)
            self._initial_screen_fit_done = True
            return
        available = screen.availableGeometry()
        usable_w = max(760, available.width() - 48)
        usable_h = max(520, available.height() - 72)
        target_w = min(usable_w, max(1000, int(available.width() * 0.90)))
        target_h = min(usable_h, max(650, int(available.height() * 0.88)))
        # Do not impose a maximum size: users must be able to resize the
        # dialog vertically and horizontally after it has opened.
        self.setMaximumSize(16777215, 16777215)
        self.resize(target_w, target_h)
        self.move(
            available.x() + (available.width() - target_w) // 2,
            available.y() + (available.height() - target_h) // 2
        )
        self._initial_screen_fit_done = True

    def _keep_dialog_visible_on_screen_change(self, screen):
        # Preserve the current size when crossing monitors. Only reposition
        # the window if it would otherwise be completely outside the new
        # screen's usable desktop area. Never resize merely because the
        # screenChanged signal fired.
        if screen is None:
            return
        available = screen.availableGeometry()
        frame = self.frameGeometry()
        x = frame.x()
        y = frame.y()
        max_x = available.x() + max(0, available.width() - frame.width())
        max_y = available.y() + max(0, available.height() - frame.height())
        new_x = min(max(x, available.x()), max_x)
        new_y = min(max(y, available.y()), max_y)
        if new_x != x or new_y != y:
            self.move(new_x, new_y)

    def _on_dialog_screen_changed(self, screen):
        self._keep_dialog_visible_on_screen_change(screen)

    def showEvent(self, event):
        super(ConverterDialog, self).showEvent(event)
        if not self._initial_screen_fit_done:
            QTimer.singleShot(0, self._fit_initial_to_available_screen)
        handle = self.windowHandle()
        if handle is not None and not self._screen_signal_connected:
            handle.screenChanged.connect(self._on_dialog_screen_changed)
            self._screen_signal_connected = True

    def _spin(self, value=0.0, decimals=6, minimum=-1e12, maximum=1e12, step=1.0):
        s = QDoubleSpinBox(); s.setDecimals(decimals); s.setRange(minimum, maximum); s.setSingleStep(step)
        s.setValue(value); s.setKeyboardTracking(False); s.setMinimumWidth(105); s.setFixedHeight(21); s.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        return s

    def _dms_row(self, degrees, minutes, seconds, directions, max_degrees):
        row = QWidget(); layout = QHBoxLayout(row); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(4)
        d = QSpinBox(); d.setRange(0, max_degrees); d.setValue(degrees); d.setSuffix('°'); d.setMinimumWidth(48); d.setFixedHeight(24); d.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        m = QSpinBox(); m.setRange(0, 59); m.setValue(minutes); m.setSuffix('′'); m.setMinimumWidth(48); m.setFixedHeight(24); m.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sec = self._spin(seconds, 3, 0, 59.999, 0.001); sec.setSuffix('″'); sec.setMinimumWidth(82); sec.setFixedHeight(24)
        hemi = QComboBox(); hemi.addItems(directions); hemi.setMinimumWidth(58); hemi.setFixedHeight(24); hemi.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(d, 1); layout.addWidget(m, 1); layout.addWidget(sec, 2); layout.addWidget(hemi, 1)
        return row, d, m, sec, hemi

    @staticmethod
    def _dms_to_decimal(d, m, sec, direction, negative_direction):
        value = float(d) + float(m) / 60.0 + float(sec) / 3600.0
        return -value if direction == negative_direction else value

    @staticmethod
    def _decimal_to_dms(value):
        value = float(value)
        absolute = abs(value)
        degrees = int(absolute)
        minute_total = (absolute - degrees) * 60.0
        minutes = int(minute_total)
        seconds = (minute_total - minutes) * 60.0
        # Avoid a displayed 60.000 seconds due to floating point rounding.
        seconds = round(seconds, 3)
        if seconds >= 60.0:
            seconds = 0.0; minutes += 1
        if minutes >= 60:
            minutes = 0; degrees += 1
        return degrees, minutes, seconds

    def _set_dms(self, value, widgets, positive_direction, negative_direction):
        d, m, sec = self._decimal_to_dms(value)
        deg_widget, min_widget, sec_widget, dir_widget = widgets
        for widget in (deg_widget, min_widget, sec_widget, dir_widget): widget.blockSignals(True)
        deg_widget.setValue(d); min_widget.setValue(m); sec_widget.setValue(sec)
        dir_widget.setCurrentText(negative_direction if value < 0 else positive_direction)
        for widget in (deg_widget, min_widget, sec_widget, dir_widget): widget.blockSignals(False)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(6)
        header = QHBoxLayout()
        logo = QLabel()
        logo_path = os.path.join(os.path.dirname(__file__), 'icon.svg')
        logo.setPixmap(QIcon(logo_path).pixmap(42, 42))
        logo.setFixedSize(46, 46)
        header.addWidget(logo)
        heading = QVBoxLayout()
        title = QLabel('GEODETIC ↔ GEOCENTRIC COORDINATE CONVERTER')
        title.setStyleSheet('font-size:17px;font-weight:bold;color:#24364b;padding:1px;')
        subtitle = QLabel('Convert between geodetic ellipsoidal coordinates (B, L, h) and geocentric Cartesian coordinates (X, Y, Z).')
        subtitle.setStyleSheet('color:#596b7c;font-size:10px;')
        heading.addWidget(title); heading.addWidget(subtitle)
        header.addLayout(heading, 1)
        root.addLayout(header)
        # Main content uses a two-column layout. Configuration panels 1 and 2
        # are stacked in the left column; the right column is reserved for the
        # illustration and calculation explanation.
        body = QHBoxLayout(); body.setSpacing(0)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(7)
        left_content = QWidget()
        left = QVBoxLayout(left_content); left.setContentsMargins(0, 0, 0, 0); left.setSpacing(2)
        left_scroll = QScrollArea(); left_scroll.setWidgetResizable(True); left_scroll.setFrameShape(QScrollArea.NoFrame)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); left_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        left_scroll.setWidget(left_content)
        # Make section headings 1–6 easier to read without enlarging the controls.
        section_title_style = (
            'QGroupBox { font-size: 10pt; font-weight: bold; }'
            'QGroupBox::title { subcontrol-origin: margin; left: 7px; padding: 0 3px; }'
        )
        ell_group = QGroupBox('1. Model ellipsoid')
        ell_group.setStyleSheet(section_title_style)
        ell_form = QFormLayout(ell_group)
        ell_form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        ell_form.setHorizontalSpacing(8); ell_form.setVerticalSpacing(1); ell_form.setContentsMargins(7, 5, 7, 5)
        self.ellipsoid_combo = QComboBox(); self.ellipsoid_combo.setFixedHeight(22); self.ellipsoid_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed); self.ellipsoid_combo.currentIndexChanged.connect(self._ellipsoid_changed)
        self.custom_check = QCheckBox('Use custom ellipsoid parameters'); self.custom_check.setFixedHeight(20); self.custom_check.toggled.connect(self._toggle_custom)
        self.a_spin = self._spin(6378137.0, 4, 1, 1e9, 1)
        self.invf_spin = self._spin(298.257223563, 9, 1.000000001, 1e9, 0.001)
        self.b_value = QLabel('6356752.314245 m'); self.f_value = QLabel('0.003352810665'); self.e2_value = QLabel('0.006694379990')
        self.a_spin.valueChanged.connect(self._ellipsoid_manual_changed); self.invf_spin.valueChanged.connect(self._ellipsoid_manual_changed)
        ell_form.addRow('Ellipsoid QGIS:', self.ellipsoid_combo); ell_form.addRow('', self.custom_check)
        ell_form.addRow('Semi-major axis a (m):', self.a_spin); ell_form.addRow('Inverse flattening (1/f):', self.invf_spin)
        ell_form.addRow('Semi-minor axis b (m):', self.b_value); ell_form.addRow('Flattening f:', self.f_value); ell_form.addRow('Eccentricity² e²:', self.e2_value)
        left.addWidget(ell_group)
        # Conversion direction is directly below the ellipsoid settings.
        mode_group = QGroupBox('2. Conversion direction'); mode_group.setStyleSheet(section_title_style)
        mode_group.setMinimumHeight(48); mode_group.setMaximumHeight(60)
        mode_layout = QVBoxLayout(mode_group)
        self.mode_combo = QComboBox(); self.mode_combo.setFixedHeight(22); self.mode_combo.addItems(['Geodetic (B, L, h) → Cartesian (X, Y, Z)', 'Cartesian (X, Y, Z) → Geodetic (B, L, h)'])
        self.mode_combo.currentIndexChanged.connect(self._mode_changed)
        mode_layout.addWidget(self.mode_combo)
        left.addWidget(mode_group)
        input_group = QGroupBox('3. Input coordinates'); input_group.setStyleSheet(section_title_style); self.input_form = QFormLayout(input_group)
        self.input_form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        self.input_form.setHorizontalSpacing(8); self.input_form.setVerticalSpacing(1); self.input_form.setContentsMargins(7, 5, 7, 5)
        # Initial coordinate: Jakarta, Indonesia (6°12′00″ S; 106°48′00″ E).
        lat_row, self.lat_deg, self.lat_min, self.lat_sec, self.lat_hemi = self._dms_row(6, 12, 0.0, ['N', 'S'], 90)
        lon_row, self.lon_deg, self.lon_min, self.lon_sec, self.lon_hemi = self._dms_row(106, 48, 0.0, ['E', 'W'], 180)
        self.lat_hemi.setCurrentText('S'); self.lon_hemi.setCurrentText('E')
        self.lat_dms = (self.lat_deg, self.lat_min, self.lat_sec, self.lat_hemi)
        self.lon_dms = (self.lon_deg, self.lon_min, self.lon_sec, self.lon_hemi)
        self.h_spin = self._spin(25, 4, -1e9, 1e9, 1)
        self.x_spin = self._spin(0, 4, -1e9, 1e9, 1); self.y_spin = self._spin(0, 4, -1e9, 1e9, 1); self.z_spin = self._spin(0, 4, -1e9, 1e9, 1)
        self.input_form.addRow('Geodetic latitude B:', lat_row); self.input_form.addRow('Geodetic longitude L:', lon_row); self.input_form.addRow('Ellipsoidal height h (m):', self.h_spin)
        self.input_form.addRow('X geocentric (m):', self.x_spin); self.input_form.addRow('Y geocentric (m):', self.y_spin); self.input_form.addRow('Z geocentric (m):', self.z_spin)
        # Keep label columns and value fields consistent across all input rows.
        for form in (ell_form, self.input_form):
            for row_index in range(form.rowCount()):
                label_item = form.itemAt(row_index, QFormLayout.LabelRole)
                if label_item is not None and label_item.widget() is not None:
                    label_item.widget().setMinimumWidth(136)
                    label_item.widget().setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        left.addWidget(input_group, 0)
        buttons = QHBoxLayout(); self.calc_btn = QPushButton('Calculate / Update'); self.calc_btn.clicked.connect(self._calculate)
        self.calc_btn.setFixedHeight(24); buttons.addWidget(self.calc_btn); left.addLayout(buttons)
        for widget in self.lat_dms + self.lon_dms:
            if isinstance(widget, QComboBox): widget.currentIndexChanged.connect(self._calculate)
            else: widget.valueChanged.connect(self._calculate)
        result_group = QGroupBox('4. Conversion results'); result_group.setStyleSheet(section_title_style); result_layout = QVBoxLayout(result_group)
        self.result_label = QLabel(''); self.result_label.setTextInteractionFlags(Qt.TextSelectableByMouse); self.result_label.setWordWrap(True)
        self.result_label.setStyleSheet('font-family:Consolas,monospace;font-size:10px;background:#f1f5f9;padding:6px;border-radius:5px;')
        result_layout.addWidget(self.result_label)
        self.quadrant_label = QLabel('Quadrant: —'); self.quadrant_label.setStyleSheet('font-weight:bold;color:#6b3fa0;font-size:9px;')
        result_layout.addWidget(self.quadrant_label); left.addWidget(result_group)
        left_scroll.setMinimumWidth(500)
        splitter.addWidget(left_scroll)
        right_panel = QWidget()
        right = QVBoxLayout(right_panel)
        right.setContentsMargins(4, 0, 0, 0)
        vis_group = QGroupBox('5. Geometry visualization'); vis_group.setStyleSheet(section_title_style); vis_layout = QVBoxLayout(vis_group)
        vis_layout.setContentsMargins(7, 7, 7, 7)
        vis_layout.setSpacing(4)
        # Reserve real vertical space for the illustration instead of letting
        # the learning panel or its labels squeeze the SVG to zero height.
        vis_group.setMinimumHeight(260)
        self.sketch = CoordinateSketch()
        self.sketch.setMinimumSize(320, 220)
        self.sketch.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        vis_layout.addWidget(self.sketch, 1)
        legend = QLabel('Left: equatorial-plane projection (x(p), y(p), λ, a). Right: meridian-plane section (Z, a, b, N+h), including detail insets for ellipsoidal height h and the Center–Qn offset.')
        legend.setWordWrap(True); legend.setStyleSheet('color:#526579;font-size:10px;'); vis_layout.addWidget(legend)
        right.addWidget(vis_group, 1)
        learn_group = QGroupBox('6. Calculation details'); learn_group.setStyleSheet(section_title_style); learn_layout = QVBoxLayout(learn_group)
        self.learning = QPlainTextEdit(); self.learning.setReadOnly(True)
        self.learning.setMinimumHeight(60); self.learning.setMaximumHeight(150)
        learn_layout.addWidget(self.learning)
        right.addWidget(learn_group, 0)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([560, 840])
        body.addWidget(splitter)
        root.addLayout(body, 1)
        foot = QLabel('The 2D diagram shows the equatorial-plane projection and meridian-plane section. The main geometry uses the ellipsoid scale; the insets enlarge the P₀–P and Center–Qn relationships for clarity.')
        foot.setWordWrap(True); foot.setMaximumHeight(34); foot.setStyleSheet('color:#6b7280;font-size:9px;padding:2px;'); root.addWidget(foot)

    def _load_ellipsoids(self):
        self._ellipsoid_data = []
        defs = QgsEllipsoidUtils.definitions()
        for definition in defs:
            parameters = definition.parameters
            if parameters.valid and parameters.semiMajor > 0 and parameters.semiMinor > 0:
                self._ellipsoid_data.append((
                    definition.acronym,
                    definition.description,
                    parameters.semiMajor,
                    parameters.inverseFlattening,
                    parameters.semiMinor
                ))
        self._ellipsoid_data.sort(key=lambda x: (0 if x[0] == 'EPSG:7030' else 1, x[1].lower()))
        self.ellipsoid_combo.blockSignals(True)
        self.ellipsoid_combo.addItem('QGIS project ellipsoid', '__PROJECT__')
        for acronym, desc, a, invf, b in self._ellipsoid_data:
            self.ellipsoid_combo.addItem('{} — {}'.format(acronym, desc), acronym)
        self.ellipsoid_combo.blockSignals(False)
        project_ell = QgsProject.instance().ellipsoid()
        idx = self.ellipsoid_combo.findData(project_ell)
        if idx < 0: idx = 0
        self.ellipsoid_combo.setCurrentIndex(idx)
        self._ellipsoid_changed(idx)

    def _toggle_custom(self, checked):
        self.ellipsoid_combo.setEnabled(not checked)
        self.a_spin.setEnabled(checked); self.invf_spin.setEnabled(checked)
        self._update_ellipsoid_labels(); self._calculate()

    def _ellipsoid_changed(self, idx):
        if self.custom_check.isChecked(): return
        key = self.ellipsoid_combo.currentData()
        if key == '__PROJECT__':
            key = QgsProject.instance().ellipsoid()
        params = QgsEllipsoidUtils.ellipsoidParameters(key)
        if params.valid and params.semiMajor > 0 and params.inverseFlattening > 1:
            self.a_spin.blockSignals(True)
            self.invf_spin.blockSignals(True)
            try:
                self.a_spin.setValue(params.semiMajor)
                self.invf_spin.setValue(params.inverseFlattening)
            finally:
                self.a_spin.blockSignals(False)
                self.invf_spin.blockSignals(False)
        self._update_ellipsoid_labels(); self._calculate()

    def _ellipsoid_manual_changed(self, *_):
        self._update_ellipsoid_labels(); self._calculate()

    def _get_ellipsoid(self):
        return ellipsoid_from_a_invf(self.a_spin.value(), self.invf_spin.value())

    def _update_ellipsoid_labels(self):
        try:
            p = self._get_ellipsoid()
            self.b_value.setText('{:.6f} m'.format(p['b']))
            self.f_value.setText('{:.12f}'.format(p['f']))
            self.e2_value.setText('{:.12f}'.format(p['e2']))
        except Exception as e:
            self.b_value.setText('—'); self.f_value.setText('—'); self.e2_value.setText(str(e))

    def _mode_changed(self, idx):
        geo = idx == 0
        for widget in self.lat_dms + self.lon_dms + (self.h_spin,): widget.setEnabled(geo)
        for widget in (self.x_spin, self.y_spin, self.z_spin): widget.setEnabled(not geo)
        self._calculate()

    def dialog_is_ready(self):
        return hasattr(self, 'sketch') and self.sketch is not None

    def _format_dms(self, value, positive_direction, negative_direction):
        d, m, sec = self._decimal_to_dms(value)
        direction = negative_direction if value < 0 else positive_direction
        return '{}° {:02d}′ {:06.3f}″ {}'.format(d, m, sec, direction)

    def _calculate(self):
        try:
            p = self._get_ellipsoid()
            if self.mode_combo.currentIndex() == 0:
                if self.lat_deg.value() == 90 and (self.lat_min.value() != 0 or self.lat_sec.value() != 0):
                    raise ValueError('At latitude 90°, minutes and seconds must be zero.')
                if self.lon_deg.value() == 180 and (self.lon_min.value() != 0 or self.lon_sec.value() != 0):
                    raise ValueError('At longitude 180°, minutes and seconds must be zero.')
                lat_input = self._dms_to_decimal(self.lat_deg.value(), self.lat_min.value(), self.lat_sec.value(), self.lat_hemi.currentText(), 'S')
                lon_input = self._dms_to_decimal(self.lon_deg.value(), self.lon_min.value(), self.lon_sec.value(), self.lon_hemi.currentText(), 'W')
                r = geodetic_to_geocentric(lat_input, lon_input, self.h_spin.value(), p['a'], self.invf_spin.value())
                x, y, z = r['x'], r['y'], r['z']
                self.x_spin.blockSignals(True); self.y_spin.blockSignals(True); self.z_spin.blockSignals(True)
                self.x_spin.setValue(x); self.y_spin.setValue(y); self.z_spin.setValue(z)
                self.x_spin.blockSignals(False); self.y_spin.blockSignals(False); self.z_spin.blockSignals(False)
                lat, lon, hh = lat_input, lon_input, self.h_spin.value()
                self.result_label.setText('X = {:+,.4f} m\nY = {:+,.4f} m\nZ = {:+,.4f} m\n\nB = {}\nL = {}\nN = {:,.4f} m'.format(x,y,z,self._format_dms(lat, 'N', 'S'),self._format_dms(lon, 'E', 'W'),r['N']))
                explanation = ('DIRECTION: GEODETIC → CARTESIAN\n\n'
                    '1. Compute the squared eccentricity: e² = {:.12f}\n'
                    '2. Compute the prime-vertical radius: N = a / √(1 − e² sin²B) = {:,.4f} m\n'
                    '3. Distance along the ellipsoid normal: N + h = {:,.4f} m\n'
                    '4. Resolve point P into geocentric Cartesian axes X, Y, and Z.\n\n'
                    'B = {:.9f}°; L = {:.9f}°; h = {:.4f} m\n'
                    'B is the angle between the ellipsoid normal and the equatorial plane, not the angle OP. N is measured from Qₙ (where the normal intersects the Z axis), not from the origin O.').format(p['e2'],r['N'],r['N']+hh,lat,lon,hh)
            else:
                r = geocentric_to_geodetic(self.x_spin.value(), self.y_spin.value(), self.z_spin.value(), p['a'], self.invf_spin.value())
                lat, lon, hh = r['lat'], r['lon'], r['h']
                self._set_dms(lat, self.lat_dms, 'N', 'S')
                self._set_dms(lon, self.lon_dms, 'E', 'W')
                self.h_spin.blockSignals(True); self.h_spin.setValue(hh); self.h_spin.blockSignals(False)
                x,y,z = self.x_spin.value(), self.y_spin.value(), self.z_spin.value()
                self.result_label.setText('B = {}\nL = {}\nh = {:+,.4f} m\n\nN = {:,.4f} m'.format(self._format_dms(lat, 'N', 'S'),self._format_dms(lon, 'E', 'W'),hh,r['N']))
                explanation = ('DIRECTION: CARTESIAN → GEODETIC\n\n'
                    '1. Compute the distance from the Z axis: ρ = √(X² + Y²) = {:,.4f} m\n'
                    '2. Determine longitude: L = atan2(Y, X) = {:.9f}°\n'
                    "3. Estimate latitude using Bowring's method.\n"
                    '4. Refine latitude and height iteratively until convergence.\n\n'
                    'B = {:.10f}°; L = {:.10f}°; h = {:.4f} m').format(math.hypot(x,y),lon,lat,lon,hh)
                if r.get('note'): explanation += '\n\nNote: ' + r['note']
            eps_xy = 1e-10 * max(1.0, abs(x), abs(y))
            if abs(x) <= eps_xy and abs(y) <= eps_xy:
                quadrant = 'Z axis (XY quadrant undefined)'
            elif abs(x) <= eps_xy:
                quadrant = 'Boundary between quadrants I and II' if y > 0 else 'Boundary between quadrants III and IV'
            elif abs(y) <= eps_xy:
                quadrant = 'Boundary between quadrants I and IV' if x > 0 else 'Boundary between quadrants II and III'
            else:
                quadrant = ('I (+X,+Y)' if x > 0 and y > 0 else
                            'II (−X,+Y)' if x < 0 and y > 0 else
                            'III (−X,−Y)' if x < 0 and y < 0 else 'IV (+X,−Y)')
            hemi = 'Northern hemisphere (positive Z)' if z > 0 else 'Southern hemisphere (negative Z)' if z < 0 else 'Equatorial plane (Z = 0)'
            self.quadrant_label.setText('XY quadrant: {}   |   Hemisphere: {}   |   Longitude direction: {}'.format(quadrant,hemi,'E' if lon >= 0 else 'W'))
            self.learning.setPlainText(explanation)
            self.sketch.update_values(lat, lon, hh, x, y, z, p['a'], p['b'])
        except Exception as e:
            self.result_label.setText('Input error: {}'.format(e))
            self.learning.setPlainText('Calculation unavailable. Check the ellipsoid parameters and input coordinates.')
