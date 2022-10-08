"""Main module"""
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from src.app import DoImageViewer
from src.core.config import Config


def main() -> None:
    """
    :return:
    """

    try:
        caminho_arquivo = sys.argv[1]
    except IndexError:
        caminho_arquivo = ""

    app = QApplication(sys.argv)

    window = DoImageViewer(app, caminho_arquivo)

    if len(sys.argv) == 3:
        window.setWindowState(Qt.WindowState.WindowMaximized)

    Config().set_config('window', 'numero', str(len(QApplication.screens())))
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
