"""Main module"""
import os
import sys
from urllib.request import urlretrieve

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from src.app import DoImageViewer
from src.core.config import Config

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

    window = None
    # noinspection PyUnresolvedReferences
    app.aboutToQuit.connect(lambda: on_exit(is_url, window))

    window = DoImageViewer(app, caminho_arquivo)

    if len(sys.argv) == 3:
        window.setWindowState(Qt.WindowState.WindowMaximized)

    Config().set_config('window', 'numero', str(len(QApplication.screens())))
    window.show()
    sys.exit(app.exec())


def on_exit(is_url: bool, window: DoImageViewer):
    if window is not None:
        window.cancelar_timer()

    if is_url:
        os.remove(CAMINHO_RES)

    try:
        screen = QApplication.screenAt(QApplication.activeWindow().pos())

        Config().set_config('window', 'nome', screen.name())

        Config().set_config(
            'window', 'tamanho',
            f'{QApplication.activeWindow().size().width()},{QApplication.activeWindow().size().height()}'
        )

        Config().set_config(
            'window', 'posicao',
            f'{QApplication.activeWindow().pos().x()},{QApplication.activeWindow().pos().y()}'
        )
    except AttributeError:
        pass


if __name__ == '__main__':
    main()
