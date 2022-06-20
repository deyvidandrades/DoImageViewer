"""Main module"""
import os
import sys
from urllib.request import urlretrieve

from PyQt6.QtWidgets import QApplication

from src.app import DoImageViewer

CAMINHO_RES = os.path.join(f'{os.getcwd()}/src/res/tmp.jpg')


def main() -> None:
    """
    :return:
    """

    try:
        caminho_arquivo = sys.argv[1]
    except IndexError:
        caminho_arquivo = ""

    # verificar o tipo de uri
    is_url = False
    if caminho_arquivo.find("http") != -1:
        urlretrieve(caminho_arquivo, CAMINHO_RES)
        caminho_arquivo = CAMINHO_RES
        is_url = True

    app = QApplication(sys.argv)

    # noinspection PyUnresolvedReferences
    app.aboutToQuit.connect(lambda: on_exit(is_url))
    window = DoImageViewer(app, caminho_arquivo)
    window.show()
    sys.exit(app.exec())


def on_exit(is_url: bool):
    if is_url:
        os.remove(CAMINHO_RES)


if __name__ == '__main__':
    main()
