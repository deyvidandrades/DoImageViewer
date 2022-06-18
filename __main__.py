"""Main module"""
import sys

from PyQt6.QtWidgets import QApplication

from src.app import DoImageViewer


def main() -> None:
    """
    :return:
    """

    try:
        caminho_arquivo = sys.argv[1]
    except IndexError:
        caminho_arquivo = ""
    # verificar o tipo de uri

    if caminho_arquivo.find("http") != -1:
        pass

    app = QApplication(sys.argv)
    window = DoImageViewer(app, caminho_arquivo)
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
