if __name__ == "__main__":
    from qtpy.QtWidgets import QApplication
    from examples.demo import DemoApp

    app = QApplication([])
    DemoApp().show()
    app.exec()
