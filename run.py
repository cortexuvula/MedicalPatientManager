import sys
from main import MedicalPatientManager
from PyQt5.QtWidgets import QApplication

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern style
    window = MedicalPatientManager()
    window.show()
    sys.exit(app.exec_())
