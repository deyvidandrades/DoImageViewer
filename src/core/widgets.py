import datetime
import math

from PyQt6.QtCore import QRect, QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QMouseEvent, QWheelEvent, QPaintEvent, QCursor, QTransform
from PyQt6.QtWidgets import QWidget, QLabel, QDialog, QVBoxLayout, QDialogButtonBox


class ImageViewer(QWidget):

    def __init__(self, parent, antialiasing: bool = True) -> None:
        super().__init__(parent)

        # Imagem
        self.m_pixmap = QPixmap()

        # Variáveis de controle
        self.m_rect = QRect()
        self.m_reference = QPoint()
        self.m_delta = QPoint()
        self.m_scale = 1.0
        self.m_mouse_global = QPoint()

        # Variaveis de configuração
        self.__arrastando_imagem = False
        self.__rotacao = 0
        self.__antialiasing = antialiasing
        self.__filtro = None

        # Iniciando o tracking do cursor e mudando para Pointing
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMouseTracking(True)

    def paintEvent(self, paint_event: QPaintEvent):
        # color burn = escurece
        # plus aviva
        # dodge aviva + escurece
        # diference equilibra + satura
        # hardLight satura
        # Overlay escurece
        # Lighten Clareia

        # atualizar label de zoom a cada alteração
        self.parent().parent().label_zoom.setText(str(math.ceil(self.m_scale * 100)) + "%")

        # desenhar a imagem
        painter = QPainter()
        painter.begin(self)
        painter.translate(paint_event.rect().center())
        painter.scale(self.m_scale, self.m_scale)
        painter.translate(self.m_delta)

        # Adiciona o filtro
        if self.__filtro is not None:
            painter.setCompositionMode(self.__filtro)

        # Adiciona filtro de suavização antialiasing
        if self.__antialiasing:
            painter.setRenderHints(
                QPainter.RenderHint.SmoothPixmapTransform |
                QPainter.RenderHint.LosslessImageRendering |
                QPainter.RenderHint.Antialiasing,
                self.__antialiasing
            )

        painter.drawPixmap(self.m_rect.topLeft(), self.m_pixmap)
        painter.end()

    def mousePressEvent(self, mouse_event: QMouseEvent):
        self.m_reference = mouse_event.pos()
        self.m_mouse_global = mouse_event.globalPosition()
        # if mouse_event.button() == Qt.MouseButton.LeftButton:
        self.__arrastando_imagem = True

        if mouse_event.button() == Qt.MouseButton.MiddleButton:
            # noinspection PyUnresolvedReferences
            self.parent().parent().exibir_cor_selecionada(self.get_posicao_mouse())

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
        :param event: Evento de 'scroll'
        :return: None
        """
        if event.angleDelta().y() > 0:
            self.__scale(.02)
        elif event.angleDelta().y() < 0:
            self.__scale(-.01)

    def __scale(self, s: float):
        # mouse_x = self.m_reference.x()
        # mouse_y = self.m_reference.y()
        # tela_x = int(self.size().width() / 2)
        # tela_y = int(self.size().height() / 2)
        # ponto_tela = QPoint(tela_x, tela_y)
        # ponto_mouse = QPoint(mouse_x, mouse_y)

        if s > 0 and self.m_scale <= 3:
            self.m_scale += s  # .02
            # if not center:
            #     self.m_delta += QPoint(
            #         int((ponto_tela.x() - ponto_mouse.x()) * .1),
            #         int((ponto_tela.y() - ponto_mouse.y()) * .1)
            #     )
            # else:
            #     self.m_delta = QPoint(0, 0)
        elif s < 0 <= self.m_scale:  # .2:
            self.m_scale += s  # .02
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
        try:
            # definição de tamanhos
            tela_y = self.parentWidget().parentWidget().height() - 73  # self.size().height()
            tela_x = self.parentWidget().parentWidget().width() - 70  # self.size().width()

            # Verifica se as dimensões estão invertidas, como resultado da rotação da imagem
            if self.__rotacao == 90 or self.__rotacao == 270:
                pixm_y = self.m_pixmap.size().width()
                pixm_x = self.m_pixmap.size().height()

                self.m_delta = (QPoint(pixm_x, pixm_y) - QPoint(pixm_y, pixm_x)) / 2
            else:
                pixm_x = self.m_pixmap.size().width()
                pixm_y = self.m_pixmap.size().height()

                self.m_delta = QPoint(0, 0)

            # definição do lado maior e da orientação da imagem
            lado_maior = max(pixm_x, pixm_y)
            vertical = False if pixm_x >= pixm_y else True

            # calculo do zoom mínimo
            if vertical:
                zoom_minimo = tela_y / lado_maior
            else:
                zoom_minimo = tela_x / lado_maior

            if lado_maior < min(tela_x, tela_y):
                zoom_minimo = round(zoom_minimo, 1)

            self.m_scale = zoom_minimo
            self.update()
        except ZeroDivisionError:
            pass

    @staticmethod
    def __verifica_igualdade_pixels(ant, atual, fator):
        # return ant == atual or \
        #    ((abs(ant.red() - atual.red()) <= fator) and (abs(ant.green() - atual.green()) <= fator) and (
        #        abs(ant.blue() - atual.blue())) <= fator)

        red_diff = abs(ant.red() - atual.red())
        green_diff = abs(ant.green() - atual.green())
        blue_diff = abs(ant.blue() - atual.blue())
        alpha_diff = abs(ant.alpha() - atual.alpha())

        # Calculate the total color difference
        total_diff = red_diff + green_diff + blue_diff + alpha_diff

        return total_diff <= fator

    def __cut_image(self, im: QPixmap, fator=3) -> (int, int, int, int):

        fator = 50

        width = im.size().width()
        height = im.size().height()

        metade_vertical = math.floor(height / 2)
        metade_horizontal = math.floor(width / 2)

        x1 = 0
        x2 = 0
        x3 = 0
        x4 = 0

        # START
        col = 1
        while col < math.floor(width / 2):
            pixel_anterior = im.toImage().pixelColor(col - 1, metade_vertical)  # getpixel((col - 1, metade_vertical))
            pixel_atual = im.toImage().pixelColor(col, metade_vertical)

            if self.__verifica_igualdade_pixels(pixel_anterior, pixel_atual, fator):
                x1 += 1
            else:
                x1 += 1
                break

            col += 1

        # END
        col = width - 2
        while col > math.floor(width / 2):
            pixel_anterior = im.toImage().pixelColor(col + 1, metade_vertical)
            pixel_atual = im.toImage().pixelColor(col, metade_vertical)

            if self.__verifica_igualdade_pixels(pixel_anterior, pixel_atual, fator):
                x2 += 1
            else:
                x2 += 1
                break

            col -= 1

        # TOP
        lin = 1
        while lin < math.floor(height / 2):
            pixel_anterior = im.toImage().pixelColor(metade_horizontal, lin - 1)
            pixel_atual = im.toImage().pixelColor(metade_horizontal, lin)

            if self.__verifica_igualdade_pixels(pixel_anterior, pixel_atual, fator):
                x3 += 1
            else:
                x3 += 1
                break

            lin += 1

        # BOT
        lin = height - 2
        while lin > math.floor(height / 2):
            pixel_anterior = im.toImage().pixelColor(metade_horizontal, lin + 1)
            pixel_atual = im.toImage().pixelColor(metade_horizontal, lin)

            if self.__verifica_igualdade_pixels(pixel_anterior, pixel_atual, fator):
                x4 += 1
            else:
                x4 += 1
                break

            lin -= 1

        return x1, width - x2, x3, height - x4

    def __crop_margem(self, pix: QPixmap) -> QPixmap:
        x, w, y, h = self.__cut_image(pix)

        # im1 = im.crop((x, y, w, h))

        return pix.copy(QRect(x, y, w, h))

    @staticmethod
    def color_difference(color1, color2, threshold):
        red_diff = abs(color1.red() - color2.red())
        green_diff = abs(color1.green() - color2.green())
        blue_diff = abs(color1.blue() - color2.blue())
        alpha_diff = abs(color1.alpha() - color2.alpha())
        total_diff = red_diff + green_diff + blue_diff + alpha_diff
        return total_diff <= threshold

    def detect_borders(self, image, width, height, fator):
        x1, x2, y1, y2 = 0, 0, 0, 0

        # Check left border
        col = 1
        while col < width / 2:
            if self.color_difference(image.pixelColor(col - 1, height // 2), image.pixelColor(col, height // 2), fator):
                x1 += 1
            else:
                x1 += 1
                break
            col += 1

        # Check right border
        col = width - 2
        while col > width / 2:
            if self.color_difference(image.pixelColor(col + 1, height // 2), image.pixelColor(col, height // 2), fator):
                x2 += 1
            else:
                x2 += 1
                break
            col -= 1

        # Check top border
        lin = 1
        while lin < height / 2:
            if self.color_difference(image.pixelColor(width // 2, lin - 1), image.pixelColor(width // 2, lin), fator):
                y1 += 1
            else:
                y1 += 1
                break
            lin += 1

        # Check bottom border
        lin = height - 2
        while lin > height / 2:
            if self.color_difference(image.pixelColor(width // 2, lin + 1), image.pixelColor(width // 2, lin), fator):
                y2 += 1
            else:
                y2 += 1
                break
            lin -= 1

        return x1, width - x2, y1, height - y2

    def crop_margins(self, pixmap, threshold):
        image = pixmap.toImage()
        width = image.width()
        height = image.height()

        x, w, y, h = self.detect_borders(image, width, height, threshold)
        return pixmap.copy(QRect(x, y, w - x, h - y))

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
        self.__scale(.02)
        self.update()

    def reduzir(self):
        self.__scale(-.02)
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

    def mudar_antialiasing(self, on: bool):
        self.__antialiasing = on

    def get_posicao_mouse(self) -> ():
        screen = self.grab()
        return screen.toImage().pixelColor(self.m_reference.x(), self.m_reference.y()).getRgb()


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
    def __init__(self, versao: str, theme, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"DoImageViewer {versao}")
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.NoButton)
        self.setStyleSheet(
            "QDialog {background-color: " + theme.color_primary +
            ";color: " + theme.color_text + ";}"
        )

        self.layout = QVBoxLayout()
        label_frase = QLabel("Um visualizador de imagens simplista")
        label_frase.setStyleSheet("color: " + theme.color_text + ";")
        label_copy = QLabel(f"Copyright {chr(0xa9)} 2021- "
                            f"{str(datetime.date.today().year)} Deyvid A. Silva <deyvid.asilva@gmail.com>")
        label_copy.setStyleSheet("color: " + theme.color_text + ";")
        label_site = QLabel(
            """<a href="https://www.github.com/deyvidandrades/doimageviewer/">
            https://www.github.com/deyvidandrades/doimageviewer/</a>"""
        )
        label_site.setStyleSheet("color: " + theme.color_text + ";")
        label_site.setOpenExternalLinks(True)

        self.layout.addWidget(label_frase)
        self.layout.addWidget(label_copy)
        self.layout.addWidget(label_site)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)
