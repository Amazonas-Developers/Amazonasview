import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel
from PySide6.QtCore import Qt

def main():
    try:
        app = QApplication(sys.argv)
        
        window = QMainWindow()
        window.setWindowTitle("Test App")
        window.setGeometry(100, 100, 400, 200)
        
        label = QLabel("¡La aplicación funciona!")
        label.setAlignment(Qt.AlignCenter)
        window.setCentralWidget(label)
        
        window.show()
        
        print("Aplicación iniciada correctamente")
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"Error: {e}")
        input("Presiona Enter para salir...")

if __name__ == "__main__":
    main()