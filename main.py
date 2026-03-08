import sys
from viewer import register_scheme

def main():
    # Custom URL scheme MUST be registered before QApplication is constructed
    register_scheme()

    from PyQt6.QtWidgets import QApplication
    from ui.main_window import MainWindow

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
