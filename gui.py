from PySide6 import QtCore, QtWidgets, QtGui
import sys
import motor_control
import encoder_control
import save_data_to_csv


class Indicator(QtWidgets.QFrame):
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        # Vertical indicator: circle on top, label below
        self.setFixedSize(72, 72)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        self.led = QtWidgets.QLabel()
        self.led.setFixedSize(28, 28)
        self.led.setStyleSheet("background: gray; border-radius:14px;")
        self.led.setAlignment(QtCore.Qt.AlignCenter)
        self.text = QtWidgets.QLabel(label)
        self.text.setStyleSheet("color: #e6e6e6;")
        self.text.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.led, alignment=QtCore.Qt.AlignHCenter)
        layout.addWidget(self.text)

    def set_color(self, color_name: str):
        # color_name: 'green', 'red', 'orange', 'grey'
        mapping = {
            'green': '#2ecc71',
            'red': '#e74c3c',
            'orange': '#f39c12',
            'grey': '#7f8c8d'
        }
        color = mapping.get(color_name, color_name)
        self.led.setStyleSheet(f"background: {color}; border-radius:14px;")


class DirectionOption(QtWidgets.QWidget):
    """Composite widget: a radio button (no text) with a large symbol label
    and a normal-sized text label. Clicking anywhere selects the radio.
    """
    def __init__(self, symbol: str, text: str, parent=None):
        super().__init__(parent)
        self.radio = QtWidgets.QRadioButton()
        self.symbol_label = QtWidgets.QLabel(symbol)
        sym_font = QtGui.QFont()
        sym_font.setPointSize(20)
        sym_font.setBold(True)
        self.symbol_label.setFont(sym_font)
        self.symbol_label.setAlignment(QtCore.Qt.AlignCenter)
        self.text_label = QtWidgets.QLabel(text)
        # keep the text label default size but slightly bold for clarity
        tfont = QtGui.QFont()
        tfont.setPointSize(10)
        tfont.setBold(False)
        self.text_label.setFont(tfont)
        self.text_label.setAlignment(QtCore.Qt.AlignCenter)
        # Let the parent widget handle mouse clicks so mousePressEvent fires on this widget
        self.symbol_label.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.text_label.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        # Show a pointer cursor so users know it's clickable
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        # top: symbol, middle: text, bottom: hidden radio to keep semantics
        layout.addWidget(self.symbol_label)
        layout.addWidget(self.text_label)
        # add radio but hide its text; clicking the widget will toggle it
        self.radio.setText('')
        self.radio.setVisible(False)
        layout.addWidget(self.radio)

    def mousePressEvent(self, event):
        # clicking anywhere sets the radio checked
        self.radio.setChecked(True)
        super().mousePressEvent(event)

    def isChecked(self) -> bool:
        return self.radio.isChecked()

    def setEnabled(self, enabled: bool):
        self.radio.setEnabled(enabled)
        self.symbol_label.setEnabled(enabled)
        self.text_label.setEnabled(enabled)

    def setChecked(self, val: bool):
        self.radio.setChecked(val)

    def set_selected(self, selected: bool):
        """Update visual appearance to indicate selected state."""
        if selected:
            # prominent background behind symbol
            self.symbol_label.setStyleSheet('background: #2e86de; color: white; border-radius: 8px; padding: 4px;')
            self.text_label.setStyleSheet('font-weight: bold; color: #ffffff;')
        else:
            self.symbol_label.setStyleSheet('background: transparent; color: #e6e6e6; padding: 4px;')
            self.text_label.setStyleSheet('font-weight: normal; color: #cfcfcf;')


class PitchMasterWindow(QtWidgets.QMainWindow):
    def __init__(self, dev_mode: bool = False):
        super().__init__()
        self.dev_mode = dev_mode
        self.bus = motor_control.init_bus(dev_mode)

        self.max_speed = None
        self.angle_data = ["null"]
        self.hlfb_data = ["null"]
        self.encoder_data = ["null"]
        self.speed = 0

        self.estop_engaged = False

        self._build_ui()

        # Initialize indicators
        self.ind_bus.set_color('green' if self.bus is not None else 'red')
        self.ind_motor.set_color('grey')
        self.ind_hlfb.set_color('grey')
        self.ind_enc.set_color('grey')

    def _build_ui(self):
        self.setWindowTitle('PitchMaster25 Control Panel')
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        outer_layout = QtWidgets.QVBoxLayout(central)
        outer_layout.setContentsMargins(8, 8, 8, 8)

        # Header: Title and version
        header_widget = QtWidgets.QWidget()
        header_layout = QtWidgets.QVBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(2)
        title = QtWidgets.QLabel('Pitch Master')
        title_font = QtGui.QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(QtCore.Qt.AlignCenter)
        version = QtWidgets.QLabel('1.0.0')
        vfont = QtGui.QFont()
        vfont.setPointSize(9)
        version.setFont(vfont)
        version.setAlignment(QtCore.Qt.AlignCenter)
        version.setStyleSheet('color: #9aa0a6;')
        header_layout.addWidget(title)
        header_layout.addWidget(version)
        outer_layout.addWidget(header_widget)

        main_layout = QtWidgets.QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Left: controls
        left_col = QtWidgets.QVBoxLayout()

        # Motor config
        cfg_group = QtWidgets.QGroupBox('Motor Configuration')
        cfg_layout = QtWidgets.QHBoxLayout()
        cfg_group.setLayout(cfg_layout)
        self.max_speed_edit = QtWidgets.QLineEdit(); self.max_speed_edit.setFixedWidth(100)
        # Max speed slider and range label
        self.max_speed_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.max_speed_slider.setMinimum(0)
        # default slider max (rpm) — user can type values beyond this but slider will clamp
        self._max_speed_slider_max = 4000
        self.max_speed_slider.setMaximum(self._max_speed_slider_max)
        self.max_speed_slider.setValue(0)
        self.max_speed_range_label = QtWidgets.QLabel(f'(Range: 0 - {self._max_speed_slider_max} rpm)')
        self.max_speed_range_label.setStyleSheet('color: #cfcfcf;')

        # Auto-apply max speed when the user types a valid number
        self.max_speed_edit.textChanged.connect(self.on_max_speed_changed)
        self.max_speed_slider.valueChanged.connect(self._max_speed_slider_changed)
        self.max_speed_edit.editingFinished.connect(self._max_speed_edit_finished)

        cfg_layout.addWidget(QtWidgets.QLabel('Max Speed (rpm):'))
        cfg_layout.addWidget(self.max_speed_edit)
        cfg_layout.addWidget(self.max_speed_slider)
        cfg_layout.addWidget(self.max_speed_range_label)
        # Removed 'Set' button — Max Speed is applied via text/slider automatically
        left_col.addWidget(cfg_group)

        # Motor panel controls - large buttons
        panel_group = QtWidgets.QGroupBox('Motor Controls')
        panel_layout = QtWidgets.QGridLayout()
        panel_group.setLayout(panel_layout)

        self.start_btn = QtWidgets.QPushButton('START')
        self.start_btn.setFixedSize(120, 60)
        self.start_btn.setStyleSheet('background: #27ae60; color: white; font-weight: bold;')
        self.start_btn.clicked.connect(self.on_start)
        self.start_btn.setEnabled(False)  # disabled until max speed set

        self.stop_btn = QtWidgets.QPushButton('STOP')
        self.stop_btn.setFixedSize(120, 60)
        self.stop_btn.setStyleSheet('background: #34495e; color: white; font-weight: bold;')
        self.stop_btn.clicked.connect(self.on_stop)
        self.stop_btn.setEnabled(False)  # disabled until max speed set

        self.estop_btn = QtWidgets.QPushButton('E-STOP')
        self.estop_btn.setFixedSize(160, 80)
        self.estop_btn.setStyleSheet('background: #b30000; color: white; font-weight: bold; font-size: 16px;')
        self.estop_btn.clicked.connect(self.on_engage_estop)

        self.release_btn = QtWidgets.QPushButton('RELEASE E-STOP')
        self.release_btn.clicked.connect(self.on_release_estop)
        self.release_btn.setVisible(False)  # only show when E-STOP is engaged

        # small controls row: parameters first, then start/stop below
        panel_layout.addWidget(QtWidgets.QLabel('Op Speed (Hz):'), 0, 0)
        # Op speed: text input + slider
        op_widget = QtWidgets.QWidget()
        op_h = QtWidgets.QHBoxLayout(op_widget)
        op_h.setContentsMargins(0,0,0,0)
        self.op_speed_edit = QtWidgets.QLineEdit(); self.op_speed_edit.setFixedWidth(80)
        self.op_speed_edit.setEnabled(False)
        self.op_speed_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.op_speed_slider.setEnabled(False)
        self.op_speed_slider.setMinimum(0)
        # Use a high-resolution slider and map it to the allowed frequency range
        self.op_speed_slider.setMaximum(1000)
        self.op_speed_slider.setValue(0)
        # Range label (updated when max_speed changes)
        self.op_range_label = QtWidgets.QLabel('(Range: 0 - 0.000 Hz)')
        self.op_range_label.setStyleSheet('color: #cfcfcf;')
        op_h.addWidget(self.op_speed_edit)
        op_h.addWidget(self.op_speed_slider)
        op_h.addWidget(self.op_range_label)
        panel_layout.addWidget(op_widget, 0, 1, 1, 2)

        # Ramp multiplier: text + slider (with visible range label)
        panel_layout.addWidget(QtWidgets.QLabel('Ramp Mult:'), 1, 0)
        ramp_widget = QtWidgets.QWidget()
        ramp_h = QtWidgets.QHBoxLayout(ramp_widget)
        ramp_h.setContentsMargins(0,0,0,0)
        self.ramp_edit = QtWidgets.QLineEdit(); self.ramp_edit.setFixedWidth(80)
        self.ramp_edit.setEnabled(False)
        self.ramp_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.ramp_slider.setEnabled(False)
        self.ramp_slider.setMinimum(0)
        self.ramp_slider.setMaximum(255)
        self.ramp_slider.setValue(50)
        # Ramp range label shown next to slider (keeps symmetry with Op Speed)
        self.ramp_range_label = QtWidgets.QLabel('(Range: 0 - 255)')
        self.ramp_range_label.setStyleSheet('color: #cfcfcf;')
        ramp_h.addWidget(self.ramp_edit)
        ramp_h.addWidget(self.ramp_slider)
        ramp_h.addWidget(self.ramp_range_label)
        panel_layout.addWidget(ramp_widget, 1, 1, 1, 2)
        # Initialize ramp text from slider
        self.ramp_edit.setText(str(self.ramp_slider.value()))

        # Direction: radio toggle with large symbol + normal text
        panel_layout.addWidget(QtWidgets.QLabel('Direction:'), 2, 0)
        dir_widget = QtWidgets.QWidget()
        dir_h = QtWidgets.QHBoxLayout(dir_widget)
        dir_h.setContentsMargins(0,0,0,0)
        self.dir_group = QtWidgets.QButtonGroup(self)
        self.dir_cw = DirectionOption('⟳', 'CW')
        self.dir_ccw = DirectionOption('⟲', 'CCW')
        self.dir_cw.setEnabled(False)
        self.dir_ccw.setEnabled(False)
        self.dir_group.addButton(self.dir_cw.radio)
        self.dir_group.addButton(self.dir_ccw.radio)
        # Ensure the group enforces exclusive selection across the composite radios
        try:
            self.dir_group.setExclusive(True)
        except Exception:
            pass
        self.dir_cw.setChecked(True)
        dir_h.addWidget(self.dir_cw)
        dir_h.addWidget(self.dir_ccw)
        panel_layout.addWidget(dir_widget, 2, 1, 1, 2)

        # Initialize direction visuals and wire toggles to update indicator
        try:
            # ensure exclusivity and update visuals
            self.dir_group.setExclusive(True)
        except Exception:
            pass
        # connect toggles to update the visual indicator
        try:
            self.dir_cw.radio.toggled.connect(self._dir_changed)
            self.dir_ccw.radio.toggled.connect(self._dir_changed)
        except Exception:
            try:
                self.dir_cw.toggled.connect(self._dir_changed)
                self.dir_ccw.toggled.connect(self._dir_changed)
            except Exception:
                pass
        # set initial visuals
        self._update_direction_indicator()

        # Place Start/Stop side-by-side and allow them to expand equally
        self.start_btn.setMinimumHeight(56)
        self.stop_btn.setMinimumHeight(56)
        self.start_btn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.stop_btn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        # make the first two columns stretch so buttons expand nicely
        panel_layout.setColumnStretch(0, 1)
        panel_layout.setColumnStretch(1, 1)
        panel_layout.addWidget(self.start_btn, 3, 0, 1, 1)
        panel_layout.addWidget(self.stop_btn, 3, 1, 1, 1)
        panel_layout.addWidget(self.estop_btn, 0, 3, 3, 1)
        panel_layout.addWidget(self.release_btn, 3, 3)

        # Connect sliders/edits to sync handlers
        self.op_speed_slider.valueChanged.connect(self._op_slider_changed)
        self.op_speed_edit.editingFinished.connect(self._op_edit_changed)
        self.ramp_slider.valueChanged.connect(self._ramp_slider_changed)
        self.ramp_edit.editingFinished.connect(self._ramp_edit_changed)
        # connect the underlying radio toggled signal from the composite widgets
        try:
            self.dir_cw.radio.toggled.connect(self._dir_changed)
            self.dir_ccw.radio.toggled.connect(self._dir_changed)
        except Exception:
            # fallback for legacy radios
            try:
                self.dir_cw.toggled.connect(self._dir_changed)
                self.dir_ccw.toggled.connect(self._dir_changed)
            except Exception:
                pass

        left_col.addWidget(panel_group)

        # Status indicators (arranged horizontally)
        status_group = QtWidgets.QGroupBox('Status Indicators')
        status_layout = QtWidgets.QHBoxLayout()
        status_group.setLayout(status_layout)
        self.ind_bus = Indicator('Bus')
        self.ind_motor = Indicator('Motor')
        self.ind_hlfb = Indicator('HLFB')
        self.ind_enc = Indicator('Encoder')
        status_layout.addWidget(self.ind_bus, alignment=QtCore.Qt.AlignHCenter)
        status_layout.addWidget(self.ind_motor, alignment=QtCore.Qt.AlignHCenter)
        status_layout.addWidget(self.ind_hlfb, alignment=QtCore.Qt.AlignHCenter)
        status_layout.addWidget(self.ind_enc, alignment=QtCore.Qt.AlignHCenter)
        left_col.addWidget(status_group)

        # Encoder controls
        enc_group = QtWidgets.QGroupBox('Encoder (Pico2)')
        enc_layout = QtWidgets.QGridLayout()
        enc_group.setLayout(enc_layout)
        enc_layout.addWidget(QtWidgets.QPushButton('Read Position', clicked=self.on_read_position), 0, 0)
        enc_layout.addWidget(QtWidgets.QLabel('Arm samples:'), 0, 1)
        self.arm_samples_edit = QtWidgets.QLineEdit('200')
        self.arm_samples_edit.setFixedWidth(80)
        enc_layout.addWidget(self.arm_samples_edit, 0, 2)
        enc_layout.addWidget(QtWidgets.QPushButton('Arm', clicked=self.on_arm_encoder), 0, 3)
        enc_layout.addWidget(QtWidgets.QPushButton('Read Encoder Data', clicked=self.on_read_encoder_data), 0, 4)
        left_col.addWidget(enc_group)

        # HLFB capture
        hlfb_group = QtWidgets.QGroupBox('HLFB Capture (Pico1)')
        hlfb_layout = QtWidgets.QHBoxLayout()
        hlfb_group.setLayout(hlfb_layout)
        hlfb_layout.addWidget(QtWidgets.QLabel('Samples:'))
        self.hlfb_samples_edit = QtWidgets.QLineEdit('50'); self.hlfb_samples_edit.setFixedWidth(80)
        hlfb_layout.addWidget(self.hlfb_samples_edit)
        hlfb_layout.addWidget(QtWidgets.QPushButton('Capture HLFB', clicked=self.on_capture_hlfb))
        left_col.addWidget(hlfb_group)

        # Save / Reset / Exit
        ops_layout = QtWidgets.QHBoxLayout()
        left_col.addLayout(ops_layout)
        ops_layout.addWidget(QtWidgets.QPushButton('Save CSV', clicked=self.on_save_csv))
        ops_layout.addWidget(QtWidgets.QPushButton('Reset', clicked=self.on_reset_all))
        ops_layout.addWidget(QtWidgets.QPushButton('Exit', clicked=self.close))

        # stretch
        left_col.addStretch()

        main_layout.addLayout(left_col, 0)

        # Right: log
        right_col = QtWidgets.QVBoxLayout()
        log_group = QtWidgets.QGroupBox('Logs / Data')
        log_layout = QtWidgets.QVBoxLayout()
        log_group.setLayout(log_layout)
        self.log_view = QtWidgets.QTextEdit()
        self.log_view.setReadOnly(True)
        font = QtGui.QFont('Courier', 10)
        self.log_view.setFont(font)
        log_layout.addWidget(self.log_view)
        right_col.addWidget(log_group)
        main_layout.addLayout(right_col, 1)

        # Attach the composed main layout under the outer vertical layout
        outer_layout.addLayout(main_layout)

    # --- Logging helper
    def log(self, msg: str):
        self.log_view.append(msg)

    # --- Control handlers mapping to existing module functions
    def on_set_max_speed(self):
        try:
            self.max_speed = float(self.max_speed_edit.text())
            self._update_motor_controls_enabled()
        except Exception:
            QtWidgets.QMessageBox.critical(self, 'Invalid', 'Max speed must be a number')

    def on_max_speed_changed(self, text: str):
        """Auto-apply max speed when the user types a valid number.
        Enables motor controls when a valid value is present, otherwise disables them.
        """
        try:
            val = float(text) if text.strip() != '' else None
        except Exception:
            val = None

        if val is not None:
            self.max_speed = val
        else:
            self.max_speed = None

        # Update motor control widgets enabled state
        self._update_motor_controls_enabled()
        # Update displayed ranges and slider mapping
        try:
            if self.max_speed is not None:
                max_op = self.max_speed / 60.0
                self.op_range_label.setText(f'(Range: 0 - {max_op:.3f} Hz)')
                # ensure current op value fits in new range
                try:
                    cur = float(self.op_speed_edit.text()) if self.op_speed_edit.text().strip() != '' else 0.0
                except Exception:
                    cur = 0.0
                if cur > max_op:
                    self.op_speed_edit.setText(f"{max_op:.3f}")
                    # update slider accordingly
                    slider_max = self.op_speed_slider.maximum() or 1000
                    self.op_speed_slider.setValue(int((max_op / max_op) * slider_max) if max_op>0 else 0)
                # keep the max_speed_slider in sync if the typed value fits slider range
                try:
                    if self.max_speed <= self._max_speed_slider_max:
                        self.max_speed_slider.setValue(int(self.max_speed))
                    else:
                        # if typed value exceeds slider max, push slider to max
                        self.max_speed_slider.setValue(self._max_speed_slider_max)
                except Exception:
                    pass
            else:
                self.op_range_label.setText('(Range: 0 - 0.000 Hz)')
        except Exception:
            pass

    def _max_speed_slider_changed(self, val: int):
        # map slider value directly to rpm and update edit box (this triggers textChanged)
        try:
            self.max_speed_edit.setText(str(val))
        except Exception:
            pass

    def _max_speed_edit_finished(self):
        # Called when user finishes editing the max speed text; ensure slider reflects the value
        try:
            val = float(self.max_speed_edit.text())
        except Exception:
            return
        try:
            if val <= self._max_speed_slider_max:
                self.max_speed_slider.setValue(int(val))
            else:
                self.max_speed_slider.setValue(self._max_speed_slider_max)
        except Exception:
            pass

    def _show_max_speed_status(self, val: float):
        # Display the small status label near the Max Speed control briefly
        try:
            text = f"Max: {float(val):.0f} rpm"
        except Exception:
            text = f"Max: {val} rpm"
        self.max_speed_status.setText(text)
        self.max_speed_status.setVisible(True)
        # hide after 3 seconds
        QtCore.QTimer.singleShot(3000, lambda: self.max_speed_status.setVisible(False))


    def _update_motor_controls_enabled(self):
        """Enable/disable motor controls based on whether max_speed is set
        and whether E-Stop is engaged.
        """
        enabled = (self.max_speed is not None) and (not self.estop_engaged)
        self.start_btn.setEnabled(enabled)
        # Allow STOP to be used if motor may be running; keep disabled if no max speed
        self.stop_btn.setEnabled(enabled)
        self.op_speed_edit.setEnabled(enabled)
        self.op_speed_slider.setEnabled(enabled)
        self.ramp_edit.setEnabled(enabled)
        self.ramp_slider.setEnabled(enabled)
        # enable radio buttons for direction
        # Direction composite widgets expose setEnabled
        try:
            self.dir_cw.setEnabled(enabled)
            self.dir_ccw.setEnabled(enabled)
        except Exception:
            # fallback for older widget forms
            self.dir_cw.setEnabled(enabled)
            self.dir_ccw.setEnabled(enabled)
        # refresh direction visual indicator to reflect enabled/disabled state
        try:
            self._update_direction_indicator()
        except Exception:
            pass

    def on_start(self):
        if self.estop_engaged:
            self.log('Cannot start: E-Stop is engaged')
            return
        if self.max_speed is None:
            QtWidgets.QMessageBox.warning(self, 'Not configured', 'Set Max Speed first')
            return
        try:
            # Read operating speed and ramp either from text fields or sliders
            op_text = self.op_speed_edit.text()
            op = float(op_text) if op_text.strip() != '' else None
            ramp_text = self.ramp_edit.text()
            ramp = int(ramp_text) if ramp_text.strip() != '' else None
            # direction composite: check underlying radio
            direction = 'cw' if (self.dir_cw.isChecked() if hasattr(self.dir_cw, 'isChecked') else self.dir_cw.radio.isChecked()) else 'ccw'

            # Validate against max_speed so we don't exceed 100% duty
            if self.max_speed is not None and op is not None:
                max_op = self.max_speed / 60.0
                if op > max_op:
                    QtWidgets.QMessageBox.warning(self, 'Invalid', f'Operating speed too high. Max allowed: {max_op:.3f} Hz')
                    return
            if ramp is not None and not (0 <= ramp <= 255):
                QtWidgets.QMessageBox.warning(self, 'Invalid', 'Ramp multiplier must be between 0 and 255')
                return
            self.log(f'Starting motor: op={op}, ramp={ramp}, dir={direction}')
            res = motor_control.start_motor(self.bus, self.max_speed, operating_speed=op, ramp_multiplier=ramp, direction_string=direction)
            if res is not None:
                self.speed = res
                self.log(f'Motor started at {self.speed} Hz')
                self.ind_motor.set_color('green')
        except Exception as e:
            self.log(f'Start failed: {e}')

    def on_stop(self):
        try:
            motor_control.stop_motor(self.bus)
            self.log('Stop command sent')
            self.ind_motor.set_color('grey')
        except Exception as e:
            self.log(f'Stop failed: {e}')

    def on_engage_estop(self):
        # Engage E-Stop: send stop, disable controls
        try:
            motor_control.emergency_stop_motor(self.bus)
        except Exception as e:
            self.log(f'E-Stop send failed: {e}')
        self.estop_engaged = True
        self.estop_btn.setText('E-STOP ENGAGED')
        self.estop_btn.setStyleSheet('background: #ff3333; color: white; font-weight: bold; font-size: 16px;')
        self.release_btn.setVisible(True)
        # disable motor controls when E-Stop is engaged
        self._update_motor_controls_enabled()
        self.ind_motor.set_color('red')
        self.log('E-Stop ENGAGED: motor power cut')

    def on_release_estop(self):
        # Simulate twist-release
        self.estop_engaged = False
        self.estop_btn.setText('E-STOP')
        self.estop_btn.setStyleSheet('background: #b30000; color: white; font-weight: bold; font-size: 16px;')
        self.release_btn.setVisible(False)
        # restore motor control enabled-state depending on max_speed
        self._update_motor_controls_enabled()
        self.ind_motor.set_color('grey')
        self.log('E-Stop released: panel re-enabled (motor remains stopped)')

    def on_read_position(self):
        try:
            val = encoder_control.read_single_sample(self.bus)
            if val is not None:
                self.log(f'Current Position: {val}')
            else:
                self.log('Failed to read position')
        except Exception as e:
            self.log(f'Read position error: {e}')

    def on_arm_encoder(self):
        try:
            if self.estop_engaged:
                self.log('Cannot arm encoder: E-Stop is engaged')
                return
            samples = int(self.arm_samples_edit.text())
            ok = encoder_control.arm_encoder(self.bus, samples=samples)
            if ok:
                self.ind_enc.set_color('green')
                self.log(f'Armed encoder for {samples} samples')
            else:
                self.log('Failed to arm encoder')
        except Exception as e:
            self.log(f'Arm encoder failed: {e}')

    def on_read_encoder_data(self):
        try:
            self.log('Attempting to read encoder data...')
            data = encoder_control.read_encoder_data(self.bus)
            if data:
                self.encoder_data = data
                self.ind_enc.set_color('green')
                self.log(f'Retrieved {len(data)} encoder samples')
            else:
                self.log('No encoder data retrieved')
        except Exception as e:
            self.log(f'Read encoder failed: {e}')

    def on_capture_hlfb(self):
        try:
            samples = int(self.hlfb_samples_edit.text())
            self.log(f'Capturing HLFB ({samples} samples)')
            self.ind_hlfb.set_color('orange')
            data = motor_control.capture_and_read_hlfb(self.bus, num_samples=samples)
            if data:
                self.hlfb_data = data
                self.angle_data = data[:]
                self.ind_hlfb.set_color('green')
                self.log(f'Captured {len(data)} HLFB samples')
            else:
                self.ind_hlfb.set_color('grey')
                self.log('No HLFB data captured')
        except Exception as e:
            self.ind_hlfb.set_color('grey')
            self.log(f'HLFB capture failed: {e}')

    # --- Slider / edit sync handlers and validation ---
    def _op_slider_changed(self, val: int):
        # Slider value is mapped to a float range; use slider range 0..slider_max representing 0..max_op
        if self.max_speed is None:
            return
        max_op = self.max_speed / 60.0
        slider_max = self.op_speed_slider.maximum() or 100
        op_val = (val / slider_max) * max_op
        # update text without triggering editingFinished (acceptable)
        self.op_speed_edit.setText(f"{op_val:.3f}")

    def _op_edit_changed(self):
        text = self.op_speed_edit.text()
        try:
            val = float(text)
        except Exception:
            return
        if self.max_speed is None:
            return
        max_op = self.max_speed / 60.0
        if val < 0:
            val = 0.0
        if val > max_op:
            val = max_op
            self.op_speed_edit.setText(f"{val:.3f}")
        slider_max = self.op_speed_slider.maximum() or 100
        slider_val = int((val / max_op) * slider_max) if max_op > 0 else 0
        self.op_speed_slider.setValue(slider_val)

    def _ramp_slider_changed(self, val: int):
        self.ramp_edit.setText(str(val))

    def _ramp_edit_changed(self):
        text = self.ramp_edit.text()
        try:
            val = int(text)
        except Exception:
            return
        if val < 0:
            val = 0
        if val > 255:
            val = 255
            self.ramp_edit.setText(str(val))
        self.ramp_slider.setValue(val)

    def _dir_changed(self, checked: bool):
        # Update visuals for direction options whenever selection changes
        try:
            self._update_direction_indicator()
        except Exception:
            pass

    def _update_direction_indicator(self):
        # Set visual selection for composite direction widgets
        try:
            cw_selected = False
            ccw_selected = False
            if hasattr(self.dir_cw, 'radio'):
                cw_selected = self.dir_cw.radio.isChecked()
            elif hasattr(self.dir_cw, 'isChecked'):
                cw_selected = self.dir_cw.isChecked()
            if hasattr(self.dir_ccw, 'radio'):
                ccw_selected = self.dir_ccw.radio.isChecked()
            elif hasattr(self.dir_ccw, 'isChecked'):
                ccw_selected = self.dir_ccw.isChecked()

            try:
                self.dir_cw.set_selected(cw_selected)
                self.dir_ccw.set_selected(ccw_selected)
            except Exception:
                # if composite doesn't support set_selected, ignore
                pass
        except Exception:
            pass

    def on_save_csv(self):
        try:
            # Ask user for filename & location using QFileDialog.getSaveFileName
            dlg = QtWidgets.QFileDialog(self)
            dlg.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
            dlg.setNameFilter('CSV Files (*.csv)')
            dlg.setDefaultSuffix('csv')
            path, _ = dlg.getSaveFileName(self, 'Save CSV', '', 'CSV Files (*.csv)')
            if path and path.strip() != '':
                save_data_to_csv.save(self.speed, self.angle_data, self.hlfb_data, self.encoder_data, file_path=path)
                self.log(f'Saved CSV to {path}')
            else:
                self.log('Save cancelled')
        except Exception as e:
            self.log(f'Save failed: {e}')

    def on_reset_all(self):
        # Reset inputs and in-memory data but do NOT release a latched E-Stop
        try:
            self.max_speed = None
            self.max_speed_edit.setText('')
            self.op_speed_edit.setText('')
            self.op_speed_slider.setValue(0)
            self.ramp_edit.setText(str(self.ramp_slider.value()))
            self.ramp_slider.setValue(self.ramp_slider.value())
            # set direction to default CW (works for composite DirectionOption)
            try:
                self.dir_cw.setChecked(True)
            except Exception:
                try:
                    self.dir_cw.radio.setChecked(True)
                except Exception:
                    pass
            self.arm_samples_edit.setText('200')
            self.hlfb_samples_edit.setText('50')
            self.angle_data = ['null']
            self.hlfb_data = ['null']
            self.encoder_data = ['null']
            self.speed = 0
            self.log_view.clear()
            self.log('State reset to defaults')
            # Update controls according to cleared max_speed / e-stop state
            self._update_motor_controls_enabled()
        except Exception as e:
            self.log(f'Reset failed: {e}')


def run_gui(dev_mode: bool = False):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    win = PitchMasterWindow(dev_mode=dev_mode)
    win.show()
    app.exec()

