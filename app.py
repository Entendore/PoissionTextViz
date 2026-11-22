import sys
import numpy as np
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QSlider, QLabel, QPushButton, 
                               QFileDialog, QTextEdit, QGroupBox, QSplitter)
from PySide6.QtCore import Qt, QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class PoissonTextVisualizer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Poisson Text Visualizer")
        self.setGeometry(100, 100, 1400, 850)
        
        self.original_text = ""
        self.lambda_x = 15
        self.lambda_y = 1
        self.lambda_z = 1
        
        self.z_mults = np.array([])
        self.y_spaces = np.array([])
        self.x_samples = []
        
        # Animation state
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate_step)
        self.is_animating = False
        self.animation_time = 0.0
        
        self.init_ui()
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # --- Left Panel: Controls ---
        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)
        control_panel.setMaximumWidth(280)
        
        file_group = QGroupBox("File Operations")
        file_layout = QVBoxLayout()
        self.load_btn = QPushButton("Load Text File")
        self.load_btn.clicked.connect(self.load_file)
        file_layout.addWidget(self.load_btn)
        self.file_label = QLabel("No file loaded")
        self.file_label.setWordWrap(True)
        file_layout.addWidget(self.file_label)
        file_group.setLayout(file_layout)
        control_layout.addWidget(file_group)
        
        self.sliders = {}
        slider_configs = [
            ("X-Axis (Rows / Line Length)", 'x', 1, 40, 15),
            ("Y-Axis (Columns / Spacing)", 'y', 0, 10, 1),
            ("Z-Axis (Depth / Multiplicity)", 'z', 0, 5, 1)
        ]
        
        for title, axis, min_val, max_val, default in slider_configs:
            group = QGroupBox(title)
            layout = QVBoxLayout()
            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(min_val)
            slider.setMaximum(max_val)
            slider.setValue(default)
            slider.valueChanged.connect(self.update_visuals)
            label = QLabel(f"λ = {slider.value()}")
            layout.addWidget(label)
            layout.addWidget(slider)
            group.setLayout(layout)
            control_layout.addWidget(group)
            self.sliders[axis] = {'slider': slider, 'label': label}
            
        # --- Animation Controls ---
        anim_group = QGroupBox("Animation Controls")
        anim_layout = QVBoxLayout()
        
        self.play_btn = QPushButton("▶ Play Animation")
        self.play_btn.setCheckable(True)
        self.play_btn.toggled.connect(self.toggle_animation)
        anim_layout.addWidget(self.play_btn)
        
        self.speed_label = QLabel("Speed: 10 FPS")
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(30)
        self.speed_slider.setValue(10)
        self.speed_slider.valueChanged.connect(self.update_animation_speed)
        anim_layout.addWidget(self.speed_label)
        anim_layout.addWidget(self.speed_slider)
        
        anim_group.setLayout(anim_layout)
        control_layout.addWidget(anim_group)
        
        control_layout.addStretch()
        
        # --- Middle Panel: Live Histograms ---
        chart_panel = QWidget()
        chart_layout = QVBoxLayout(chart_panel)
        chart_panel.setMaximumWidth(350)
        
        self.figure = Figure(figsize=(4, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.ax_x = self.figure.add_subplot(311)
        self.ax_y = self.figure.add_subplot(312)
        self.ax_z = self.figure.add_subplot(313)
        
        chart_layout.addWidget(self.canvas)
        
        # --- Right Panel: Rich Text Views ---
        text_panel = QWidget()
        text_layout = QVBoxLayout(text_panel)
        
        splitter = QSplitter(Qt.Vertical)
        
        orig_group = QGroupBox("Original Text (Diff / Map View)")
        orig_layout = QVBoxLayout()
        self.original_edit = QTextEdit()
        self.original_edit.setReadOnly(True)
        orig_layout.addWidget(self.original_edit)
        orig_group.setLayout(orig_layout)
        splitter.addWidget(orig_group)
        
        adj_group = QGroupBox("Poisson Adjusted Text (Result View)")
        adj_layout = QVBoxLayout()
        self.adjusted_edit = QTextEdit()
        self.adjusted_edit.setReadOnly(True)
        adj_layout.addWidget(self.adjusted_edit)
        adj_group.setLayout(adj_layout)
        splitter.addWidget(adj_group)
        
        text_layout.addWidget(splitter)
        
        main_layout.addWidget(control_panel)
        main_layout.addWidget(chart_panel)
        main_layout.addWidget(text_panel)
        
    def load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Text File", "", "Text Files (*.txt);;All Files (*.*)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.original_text = f.read()
                self.file_label.setText(f"Loaded: {file_path.split('/')[-1]}")
                self.update_visuals()
            except Exception as e:
                self.file_label.setText(f"Error: {str(e)}")

    # --- Animation Methods ---
    def toggle_animation(self, checked):
        if checked:
            self.play_btn.setText("⏸ Pause Animation")
            self.is_animating = True
            self.update_animation_speed()
            self.animation_timer.start()
        else:
            self.play_btn.setText("▶ Play Animation")
            self.animation_timer.stop()
            self.is_animating = False

    def update_animation_speed(self):
        speed = self.speed_slider.value()
        self.speed_label.setText(f"Speed: {speed} FPS")
        if self.is_animating:
            # Set timer interval in milliseconds based on desired FPS
            self.animation_timer.setInterval(int(1000 / speed))

    def animate_step(self):
        # Increment time for sine wave calculation
        self.animation_time += 0.15
        
        # Oscillate sliders using sine waves with different frequencies and phases
        # This ensures they don't all move in perfect, boring sync
        x_val = self._map_sine(self.animation_time * 0.5, self.sliders['x']['slider'])
        self.sliders['x']['slider'].setValue(x_val)
        
        y_val = self._map_sine(self.animation_time * 0.8 + 2.0, self.sliders['y']['slider'])
        self.sliders['y']['slider'].setValue(y_val)
        
        z_val = self._map_sine(self.animation_time * 0.6 + 4.0, self.sliders['z']['slider'])
        self.sliders['z']['slider'].setValue(z_val)

    def _map_sine(self, t, slider):
        # Maps a sine wave (-1 to 1) to the slider's min/max range
        norm = (np.sin(t) + 1.0) / 2.0
        min_val = slider.minimum()
        max_val = slider.maximum()
        return int(min_val + norm * (max_val - min_val))

    # --- Visualization Methods ---
    def update_visuals(self):
        for axis in ['x', 'y', 'z']:
            val = self.sliders[axis]['slider'].value()
            self.sliders[axis]['label'].setText(f"λ = {val}")
            
        self.lambda_x = self.sliders['x']['slider'].value()
        self.lambda_y = self.sliders['y']['slider'].value()
        self.lambda_z = self.sliders['z']['slider'].value()
        
        if not self.original_text:
            self.original_edit.clear()
            self.adjusted_edit.clear()
            return
            
        self.generate_visualization()
        
    def escape_html(self, text):
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace(' ', '&nbsp;')

    def generate_visualization(self):
        # Reduced to 1500 to maintain smooth animation framerates
        MAX_CHARS = 1500
        text_to_process = self.original_text
        truncated = False
        if len(self.original_text) > MAX_CHARS:
            text_to_process = self.original_text[:MAX_CHARS]
            truncated = True
            
        n = len(text_to_process)
        
        self.z_mults = np.random.poisson(self.lambda_z, n)
        self.y_spaces = np.random.poisson(self.lambda_y, n)
        self.x_samples = []
        
        orig_html = []
        adj_html = []
        
        line_limit = max(1, np.random.poisson(self.lambda_x))
        char_count = 0
        
        for i, char in enumerate(text_to_process):
            if char == '\n':
                orig_html.append('<br>')
                adj_html.append('<br>')
                line_limit = max(1, np.random.poisson(self.lambda_x))
                char_count = 0
                continue
                
            mult = self.z_mults[i]
            spaces = self.y_spaces[i]
            esc_char = self.escape_html(char)
            
            # --- Original Text HTML (Diff View) ---
            if mult == 0:
                orig_html.append(f'<span style="color: red; text-decoration: line-through;">{esc_char}</span>')
            elif mult > 1:
                orig_html.append(f'<span style="color: darkgreen; text-decoration: underline;">{esc_char}</span>')
            else:
                orig_html.append(esc_char)
                
            if spaces > 0:
                orig_html.append(f'<span style="background-color: #e0e0ff;">{"&nbsp;" * spaces}</span>')
                
            # --- Adjusted Text HTML (Result View) ---
            if mult > 0:
                adj_char = esc_char * mult
                
                if mult == 1:
                    style = "color: #222222;"
                elif mult == 2:
                    style = "color: #0000AA; background-color: #E0F0FF;"
                elif mult == 3:
                    style = "color: #6600CC; background-color: #F0E0FF;"
                elif mult == 4:
                    style = "color: #CC0000; background-color: #FFE0E0;"
                else:
                    style = "color: #8B0000; background-color: #FFC0C0;"
                    
                adj_html.append(f'<span style="{style}">{adj_char}</span>')
                
            if spaces > 0:
                adj_html.append(f'<span style="background-color: #e0e0ff;">{"&nbsp;" * spaces}</span>')
                
            char_count += 1
            
            if char_count >= line_limit:
                self.x_samples.append(line_limit)
                orig_html.append('<span style="background-color: #ffe0e0; color: #ff9999;">|</span>')
                adj_html.append('<br>')
                line_limit = max(1, np.random.poisson(self.lambda_x))
                char_count = 0

        if truncated:
            orig_html.append('<br><span style="color: red;">... [Truncated for performance] ...</span>')
            adj_html.append('<br><span style="color: red;">... [Truncated for performance] ...</span>')

        self.original_edit.setHtml("".join(orig_html))
        self.adjusted_edit.setHtml("".join(adj_html))
        
        self.update_histograms()

    def update_histograms(self):
        self.ax_x.clear()
        self.ax_y.clear()
        self.ax_z.clear()
        
        if self.x_samples:
            max_x = max(self.x_samples)
            self.ax_x.hist(self.x_samples, bins=range(0, max_x + 2), color='skyblue', edgecolor='black', align='left')
        self.ax_x.set_title(f'X (Rows) λ={self.lambda_x}', fontsize=10)
        self.ax_x.set_ylabel('Count', fontsize=8)
        self.ax_x.tick_params(axis='both', labelsize=8)
        
        if len(self.y_spaces) > 0:
            max_y = max(self.y_spaces)
            self.ax_y.hist(self.y_spaces, bins=range(0, max_y + 2), color='lightgreen', edgecolor='black', align='left')
        self.ax_y.set_title(f'Y (Cols) λ={self.lambda_y}', fontsize=10)
        self.ax_y.set_ylabel('Count', fontsize=8)
        self.ax_y.tick_params(axis='both', labelsize=8)
        
        if len(self.z_mults) > 0:
            max_z = max(self.z_mults)
            self.ax_z.hist(self.z_mults, bins=range(0, max_z + 2), color='salmon', edgecolor='black', align='left')
        self.ax_z.set_title(f'Z (Depth) λ={self.lambda_z}', fontsize=10)
        self.ax_z.set_xlabel('Value', fontsize=8)
        self.ax_z.set_ylabel('Count', fontsize=8)
        self.ax_z.tick_params(axis='both', labelsize=8)
        
        self.figure.tight_layout()
        self.canvas.draw()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = PoissonTextVisualizer()
    window.show()
    sys.exit(app.exec())