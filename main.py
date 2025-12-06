if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    from examples.demo import DemoApp

    app = QApplication([])
    DemoApp().show()
    app.exec()
