import datetime
import math

from PyQt6.QtCore import QRect, QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QMouseEvent, QWheelEvent, QPaintEvent, QCursor, QTransform
from PyQt6.QtWidgets import QWidget, QLabel, QDialog, QVBoxLayout, QDialogButtonBox


class ImageViewer(QWidget):

    def __init__(self, parent) -> None:
        super().__init__(parent)

        # Imagem
        self.m_pixmap = QPixmap()

        # Variáveis de controle
        self.m_rect = QRect()
        self.m_reference = QPoint()
        self.m_delta = QPoint()
        self.m_scale = 1.0

        # Variaveis de configuração
        self.__arrastando_imagem = False
        self.__rotacao = 0

        # Iniciando o tracking do cursor e mudando para Pointing
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMouseTracking(True)

    def paintEvent(self, paint_event: QPaintEvent):

        # atualizar label de zoom a cada alteração
        self.parent().parent().label_zoom.setText(str(math.ceil(self.m_scale * 100)) + "%")

        # desenhar a imagem
        painter = QPainter()
        painter.begin(self)
        painter.translate(paint_event.rect().center())
        painter.scale(self.m_scale, self.m_scale)
        painter.translate(self.m_delta)
        painter.drawPixmap(self.m_rect.topLeft(), self.m_pixmap)
        painter.end()

    def mousePressEvent(self, mouse_event: QMouseEvent):
        self.m_reference = mouse_event.pos()
        # if mouse_event.button() == Qt.MouseButton.LeftButton:
        self.__arrastando_imagem = True

    def mouseReleaseEvent(self, mouse_event: QMouseEvent):
        self.__arrastando_imagem = False

    def mouseMoveEvent(self, mouse_event: QMouseEvent):
        if self.__arrastando_imagem:
            self.m_delta += (mouse_event.pos() - self.m_reference) * 1.0 / self.m_scale

        self.m_reference = mouse_event.pos()
        self.update()

    def wheelEvent(self, event: QWheelEvent):
        """
        Sobrescrição do método da superclasse
        :param event: Evento de 'scroll' do mouse
        :return: None
        """
        if event.angleDelta().y() > 0:
            self.__scale(.05)
        elif event.angleDelta().y() < 0:
            self.__scale(-.05)

    def __scale(self, s: float):
        # mouse_x = self.m_reference.x()
        # mouse_y = self.m_reference.y()
        # tela_x = int(self.size().width() / 2)
        # tela_y = int(self.size().height() / 2)
        # ponto_tela = QPoint(tela_x, tela_y)
        # ponto_mouse = QPoint(mouse_x, mouse_y)

        if s > 0 and self.m_scale <= 3:
            self.m_scale += .05
            # if not center:
            #     self.m_delta += QPoint(
            #         int((ponto_tela.x() - ponto_mouse.x()) * .1),
            #         int((ponto_tela.y() - ponto_mouse.y()) * .1)
            #     )
            # else:
            #     self.m_delta = QPoint(0, 0)
        elif s < 0 and self.m_scale >= .2:
            self.m_scale -= .05
            # if not center:
            #     self.m_delta -= QPoint(
            #         int((ponto_tela.x() - ponto_mouse.x()) * .1),
            #         int((ponto_tela.y() - ponto_mouse.y()) * .1)
            #     )
            # else:
            #     self.m_delta = QPoint(0, 0)

        if self.m_scale <= .5:
            if self.__rotacao == 90 or self.__rotacao == 270:
                pixm_y = self.m_pixmap.size().width()
                pixm_x = self.m_pixmap.size().height()

                self.m_delta = (QPoint(pixm_x, pixm_y) - QPoint(pixm_y, pixm_x)) / 2
            else:
                self.m_delta = QPoint(0, 0)

        self.update()

    def __calcular_centro(self):

        # if self.__rotacao == 90 or self.__rotacao == 270:
        #     self.m_delta = QPoint(self.m_delta.y(),self.m_delta.x())
        #     self.update()

        # tela_x = int(self.m_pixmap.size().width() / 4)
        # tela_y = int(self.m_pixmap.size().height() / 4)
        # print(QPoint(tela_x, tela_y))
        # print(QPoint(tela_y, tela_x))
        # self.m_delta = QPoint(tela_y, tela_x)

        try:
            tela_x = self.parent().parent().width()
            tela_y = self.parent().parent().height()
            pixm_x = self.m_pixmap.size().width()
            pixm_y = self.m_pixmap.size().height()

            if self.__rotacao == 90 or self.__rotacao == 270:
                pixm_y = self.m_pixmap.size().width()
                pixm_x = self.m_pixmap.size().height()

                self.m_delta = (QPoint(pixm_x, pixm_y) - QPoint(pixm_y, pixm_x)) / 2
            else:
                self.m_delta = QPoint(0, 0)

            x = round(tela_x / pixm_x, 3)
            y = round(tela_y / pixm_y, 3)

            # minimo = (x if max(x, y) > .5 else .5) - .1
            if pixm_x > pixm_y:
                minimo = (x if x > .5 else .5) - .1
            else:
                minimo = (y if y > .5 else .5) - .1

            if minimo > 1:
                minimo = 1

            # if tela_x > 800 and minimo > 1:
            #     minimo_maximizado = minimo - (
            #             (max(tela_x, tela_y) - max(pixm_x, pixm_y)) / max(pixm_x, pixm_y) + .1
            #     ) + .4
            #
            #     if minimo_maximizado > 0:
            #         minimo = minimo_maximizado

            #     if pixm_x > pixm_y:
            #         minimo = ((tela_x - pixm_x) / pixm_x + .1)
            #     else:
            #         minimo = ((tela_y - pixm_y) / pixm_y + .1)

            self.m_scale = minimo

            self.update()
        except ZeroDivisionError:
            pass

    def adicionar_imagem(self, pixmap: QPixmap) -> None:
        self.m_pixmap = pixmap

        self.m_rect = self.m_pixmap.rect()
        self.m_rect.translate(-self.m_rect.center())

        self.__rotacao = 0
        self.__calcular_centro()

    def rotacionar(self, direcao: str):
        rotacao = 90
        if direcao == 'dir':
            self.__rotacao += 90
        else:
            self.__rotacao -= -90
            rotacao *= -1

        if self.__rotacao >= 360:
            self.__rotacao = 0

        if self.__rotacao <= -360:
            self.__rotacao = 360

        rm = QTransform()
        rm.rotate(rotacao)
        self.m_pixmap = self.m_pixmap.transformed(rm)
        self.__calcular_centro()
        self.update()

    def ampliar(self):
        self.__scale(.5)
        self.update()

    def reduzir(self):
        self.__scale(-.5)
        self.update()

    def centralizar(self):
        self.m_delta = QPoint(0, 0)
        self.__calcular_centro()

    def inverter_horizontal(self):
        rm = QTransform()
        rm.scale(-1, 1)
        self.m_pixmap = self.m_pixmap.transformed(rm)
        self.update()

    def inverter_vertical(self):
        rm = QTransform()
        rm.scale(1, -1)
        self.m_pixmap = self.m_pixmap.transformed(rm)
        self.update()


class QLabelClick(QLabel):
    """
    Reimplementação da classe QLabel()
    """
    clicked = pyqtSignal()

    def mousePressEvent(self, ev: QMouseEvent) -> None:
        """
        Método sobrescrito da superclasse
        :param ev: evento de clique do mouse
        :return: None
        """
        # noinspection PyUnresolvedReferences
        self.clicked.emit()


class SobreDialog(QDialog):
    def __init__(self, versao: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"DoImageViewer {versao}")
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.NoButton)

        self.layout = QVBoxLayout()
        label_frase = QLabel("Um visualizador de imagens simplista")
        label_copy = QLabel(f"Copyright {chr(0xa9)} 2021- "
                            f"{str(datetime.date.today().year)} Deyvid A. Silva <deyvid.asilva@gmail.com>")
        label_site = QLabel(
            """<a href="https://www.github.com/deyvidandrades/doimageviewer/">
            https://www.github.com/deyvidandrades/doimageviewer/</a>"""
        )
        label_site.setOpenExternalLinks(True)

        self.layout.addWidget(label_frase)
        self.layout.addWidget(label_copy)
        self.layout.addWidget(label_site)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)
