if __name__ == "__main__":
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from PySide6.QtWidgets import QApplication
    else:
        from qtpy.QtWidgets import QApplication
    from examples.demo import DemoApp

    app = QApplication([])
    DemoApp().show()
    app.exec()
