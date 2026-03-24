import sys
from datetime import datetime

from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QWidget,
    QVBoxLayout, QPushButton, QLineEdit, QHBoxLayout, QTextEdit
)
from PyQt6.QtCore import Qt
from Fuzzification import Inference

class Inputs:
    def __init__(self):
        # layout input-uri
        self.input_layout = QHBoxLayout()
        self.input_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.input_layout.setSpacing(10)

        # input-uri
        self.cpi_input = QLineEdit()
        self.cpi_input.setPlaceholderText("CPI")

        self.funds_rate = QLineEdit()
        self.funds_rate.setPlaceholderText("Funds Rate")

        self.dollar_index = QLineEdit()
        self.dollar_index.setPlaceholderText("Dollar Index")

        self.geopolitical_tension_input = QLineEdit()
        self.geopolitical_tension_input.setPlaceholderText("Geopolitical")

        self.vix_input = QLineEdit()
        self.vix_input.setPlaceholderText("VIX")

        self.banks_demand_input = QLineEdit()
        self.banks_demand_input.setPlaceholderText("Banks Demand")

        # adăugare input-uri
        self.input_layout.addWidget(self.cpi_input)
        self.input_layout.addWidget(self.funds_rate)
        self.input_layout.addWidget(self.dollar_index)
        self.input_layout.addWidget(self.geopolitical_tension_input)
        self.input_layout.addWidget(self.vix_input)
        self.input_layout.addWidget(self.banks_demand_input)


class Color(QWidget):
    def __init__(self, color):
        super().__init__()
        self.setAutoFillBackground(True)

        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(color))
        self.setPalette(palette)

class Infer:
    def __init__(self, inputs):
        self.data = None
        self.result = None
        self.fuzzified_data = None
        self.item = None
        self.inputs = inputs
        self.inference = Inference()

    def generate_trend(self):
        now = datetime.now()
        analyzed_date = now.strftime("%Y-%m-%d")
        generated_at = now.strftime("%Y-%m-%d %H:%M:%S")
        self.data = {
            "analyzed_date": analyzed_date,
            "generated_at": generated_at,
            "variables_fuzzy": {
                "inflation_cpi": float(self.inputs.cpi_input.text()),
                "fed_funds_rate": float(self.inputs.funds_rate.text()),
                "dolar_index": float(self.inputs.dollar_index.text()),
                "geopolitical_sentiment": float(self.inputs.geopolitical_tension_input.text()),
                "vix_index": float(self.inputs.vix_input.text()),
                "banks_demand": float(self.inputs.banks_demand_input.text()),
            }
        }
        self.item = {
            "date": self.data["analyzed_date"],
            "values": self.data["variables_fuzzy"]
        }
        self.fuzzified_data = self.inference.fuzzify_all([self.item])
        self.result = self.inference.infer_for_date(self.item["date"], self.fuzzified_data)
        return self.result



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gold-Trend")

        self.widget = QWidget()
        self.setCentralWidget(self.widget)
        self.setFixedSize(800, 600)

        # layout principal
        self.main_layout = QVBoxLayout()
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # buton
        self.submit_button = QPushButton("Submit")
        self.submit_button.setFixedWidth(150)
        self.submit_button.setFixedHeight(40)

        # output
        self.output_box = QTextEdit()
        self.output_box.setFixedHeight(100)
        self.output_box.setReadOnly(True)
        self.output_box.setPlaceholderText("Output will appear here...")

        # layout final
        self.inputs = Inputs()
        self.main_layout.addLayout(self.inputs.input_layout)
        self.main_layout.addSpacing(20)

        self.main_layout.addWidget(self.submit_button, alignment=Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addSpacing(20)

        self.main_layout.addWidget(self.output_box)

        self.widget.setLayout(self.main_layout)

        self.infer = Infer(self.inputs)
        self.submit_button.clicked.connect(self.handle_submit)

    def handle_submit(self):
        try:
            result = self.infer.generate_trend()

            if result:
                text = (
                    f"Date: {result['date']}\n"
                    f"Score: {result['score']}\n"
                    f"Trend: {result['trend']}\n\n"
                    f"Rules:\n"
                )

                for mu, value, name in result["rules"]:
                    text += f"{name}: mu={mu:.4f}, value={value}\n"

                self.output_box.setText(text)
            else:
                self.output_box.setText("No result")

        except Exception as e:
            self.output_box.setText(f"Error: {e}")


app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()