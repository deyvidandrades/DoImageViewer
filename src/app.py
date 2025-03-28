import os
import platform
import random
from dataclasses import dataclass
from datetime import datetime
from math import floor
from pathlib import Path
from subprocess import Popen
from threading import Timer
from urllib.error import HTTPError
from urllib.request import urlretrieve

import pilgram
from PIL import Image, ImageEnhance
from PyQt6.QtCore import QDir, Qt, QSize, QEvent, QPoint
from PyQt6.QtGui import QIcon, QPixmap, QCursor, QAction
from PyQt6.QtWidgets import QMainWindow, QMenu, QLabel, QHBoxLayout, QWidget, QFileDialog, QApplication, QToolBar, \
    QSizePolicy, QMessageBox

from src.core.config import Config
from src.core.widgets import ImageViewer, QLabelClick, SobreDialog

from showinfm import show_in_file_manager


@dataclass
class Theme:
    color_primary: str = '#1b2224'
    color_secondary: str = '#263033'
    color_text: str = '#fafafa'
    color_accent: str = '#1D63D1'


class DoImageViewer(QMainWindow):
    __RESOURCES = os.getcwd() + "/src/res/"
    __CAMINHO_HOME = f'{str(Path.home())}/.DoImageViewer/'
    __VERSAO = 'v1.6.0'
    __LISTA_EXTENSOES = ['jpg', 'jpeg', 'png', 'bmp', 'tif', 'webp']

    # noinspection PyUnresolvedReferences
    def __init__(self, app: QApplication, caminho: str = ""):
        super().__init__()

        # Configurando pasta de configurações
        if not os.path.isdir(self.__CAMINHO_HOME):
            os.mkdir(self.__CAMINHO_HOME)

        # carregar configurações
        config = Config()
        if config.get_config('editor', 'caminho') == "\"\"":
            config.set_config('editor', 'caminho', QDir.homePath() + '/')

        antialiasing = config.get_config_boolean('editor', 'antialiasing')

        # widget da aplicação
        app.aboutToQuit.connect(self.on_exit)
        self.__app = app

        # configurações da tela
        self.setStyleSheet(
            "QMainWindow {background-color: " + Theme.color_primary +
            ";color: " + Theme.color_text + ";}"
        )
        self.setWindowIcon(QIcon(QPixmap(self.__RESOURCES + 'image-svgrepo-com.svg')))
        self.setWindowTitle(f"Do Image Viewer {self.__VERSAO}")
        self.setAutoFillBackground(True)

        tela = self.__app.primaryScreen().size()
        self.resize(int(tela.width() * .45), int(tela.height() * .9))

        self.move(QPoint(config.get_window_info('posicao')[0], config.get_window_info('posicao')[1]))
        self.resize(QSize(config.get_window_info('tamanho')[0], config.get_window_info('tamanho')[1]))

        # verificar se a janela está em um monitor desconectado e movendo para o centro da tela
        if config.get_window_info('posicao')[0] > self.screen().size().width() and int(
                config.get_config('window', 'numero')) == 1:
            self.resize(int(tela.width() * .45), int(tela.height() * .9))
            self.move(QPoint(int(tela.width() / 2), int(tela.height() / 2)))

        # variáveis de controle
        self.__viewer = ImageViewer(parent=self, antialiasing=antialiasing)
        # self.__caminho = self.__processar_caminho(caminho)
        self.__diretorio_tool_bar = QToolBar("Diretorio", self)
        self.__diretorio_tool_bar.setVisible(config.get_config_boolean('editor', 'toolbar_diretorio'))
        self.tamanho_icones = QSize(24, 24)

        # Variaveis de edição de imagem
        self.__enhance = 1.0
        self.__nitidez = 1.0

        # timer da apresentação de slides
        self.__timer_interval = 3.5
        self.__timer = Timer(self.__timer_interval, self.__slide_show)

        # labels
        self.label_tamanho = QLabel("")
        self.label_lista = QLabel("Nenhuma foto carregada")
        self.label_zoom = QLabel("")

        self.label_cor = QLabelClick("")
        self.label_cor.clicked.connect(lambda: self.__copiar_cor_para_transferencia())
        self.label_cor.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.label_cor_nome = QLabelClick("")
        self.label_cor_nome.clicked.connect(lambda: self.__copiar_cor_para_transferencia())
        self.label_cor_nome.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.__label_diretorio = QLabelClick()

        # configuração do layout principal
        self.__layout_principal = QHBoxLayout()
        self.__layout_principal.setContentsMargins(5, 0, 5, 0)
        self.setAcceptDrops(True)

        self.__centralWidget = QWidget(self)
        self.setCentralWidget(self.__centralWidget)
        self.__centralWidget.setLayout(self.__layout_principal)

        # configuração da interface
        self.__configurar_gui()
        self.__configurar_menu()
        self.__configurar_tool_bar()
        self.__configurar_status_bar()

        # Verifica se é url
        if caminho.find("http") != -1:
            self.__carregar_imagem(self.__processar_url(caminho))
        else:
            self.__carregar_imagem(caminho)

        self.setWindowTitle(f"Do Image Viewer {self.__VERSAO}")

    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            if event.oldState() and Qt.WindowState.WindowMinimized:
                self.__viewer.centralizar()

            elif event.oldState() == Qt.WindowState.WindowNoState or \
                    self.windowState() == Qt.WindowState.WindowMaximized:
                self.__viewer.centralizar()

            elif event.oldState() == Qt.WindowState.WindowFullScreen:
                self.__viewer.centralizar()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]

        if files:
            self.__carregar_imagem(files[0])

    def on_exit(self):
        self.cancelar_timer()

        lista_imagens_raw = [x for x in os.listdir(self.__CAMINHO_HOME) if x.find('.') != -1]
        lista_imagens_remover = [x for x in lista_imagens_raw if x.split('.')[1] in self.__LISTA_EXTENSOES]

        for item in lista_imagens_remover:
            os.remove(f'{self.__CAMINHO_HOME}/{item}')

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

    def __processar_url(self, url: str) -> str:
        formato = None
        caminho = Path.home()

        for item in self.__LISTA_EXTENSOES:
            if url.find(item) != -1:
                formato = item

        if formato is not None:
            caminho = f'{self.__CAMINHO_HOME}/tmp.{formato}'
            try:
                urlretrieve(url, caminho)
            except HTTPError:
                pass

        return caminho

    def __configurar_gui(self):

        # Labels para mudar a imagem
        self.label_left = QLabelClick()
        self.label_left.setPixmap(QPixmap(self.__RESOURCES + 'left-svgrepo-com.svg').scaled(self.tamanho_icones))
        self.label_left.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.label_left.clicked.connect(lambda: self.__mudar_imagem('esq'))
        self.label_left.setHidden(True)

        self.label_right = QLabelClick()
        self.label_right.setPixmap(QPixmap(self.__RESOURCES + 'right-svgrepo-com.svg').scaled(self.tamanho_icones))
        self.label_right.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.label_right.clicked.connect(lambda: self.__mudar_imagem('dir'))
        self.label_right.setHidden(True)

        # Configuração do layout
        self.__layout_principal.addWidget(self.label_left)
        self.__layout_principal.addWidget(self.__viewer, 1)
        self.__layout_principal.addWidget(self.label_right)

    # noinspection PyUnresolvedReferences
    def __configurar_menu(self):
        # Style
        stylesheet = "QMenu {background-color:" + Theme.color_secondary + \
                     ";}QMenu::item{color:" + Theme.color_text + \
                     ";}QMenu::item:selected {background-color: " + Theme.color_accent + \
                     ";color:" + Theme.color_text + ";}"

        # MENU ARQUIVO
        abrir_foto = QAction("&Abrir", self)
        abrir_foto.setShortcut("Ctrl+O")
        abrir_foto.triggered.connect(self.__abrir_imagem)

        array_actions = Config().get_config('editor', 'recentes').split(',')

        menu_abrir_recentes = QMenu("&Abrir recentes", self)
        menu_abrir_recentes.setStyleSheet(stylesheet)

        acao_1 = QAction(array_actions[0], self)
        acao_1.setShortcut("Ctrl+Shift+1")
        acao_1.triggered.connect(lambda: self.__carregar_imagem(array_actions[0]))

        acao_2 = QAction(array_actions[1], self)
        acao_2.setShortcut("Ctrl+Shift+2")
        acao_2.triggered.connect(lambda: self.__carregar_imagem(array_actions[1]))

        acao_3 = QAction(array_actions[2], self)
        acao_3.setShortcut("Ctrl+Shift+3")
        acao_3.triggered.connect(lambda: self.__carregar_imagem(array_actions[2]))

        menu_abrir_recentes.addActions([acao_1, acao_2, acao_3])

        menu_abrir_janela = QAction("Nova janela", self)
        menu_abrir_janela.setShortcut("Ctrl+N")
        menu_abrir_janela.triggered.connect(self.__abrir_nova_janela)

        menu_abrir_em_janela = QAction("&Abrir em nova janela", self)
        menu_abrir_em_janela.setShortcut("Ctrl+Shift+O")
        menu_abrir_em_janela.triggered.connect(self.__abrir_foto_nova_janela)

        menu_abrir_file_manager = QAction("Mostrar na pasta", self)
        menu_abrir_file_manager.setShortcut("Ctrl+Shift+F")
        menu_abrir_file_manager.triggered.connect(self.__abrir_file_manager)

        salvar_foto = QAction("Salvar", self)
        salvar_foto.setShortcut("Ctrl+S")
        salvar_foto.triggered.connect(self.__salvar_imagem)

        salvar_foto_como = QAction("&Salvar como ...", self)
        salvar_foto_como.setShortcut("Ctrl+Shift+S")
        salvar_foto_como.triggered.connect(self.__salvar_imagem_como)

        sair = QAction("Sair", self)
        sair.setShortcut("Esc")
        sair.triggered.connect(lambda: self.__app.exit(0))

        menu_arquivo = QMenu("&Arquivo", self)
        menu_arquivo.setStyleSheet(stylesheet)
        menu_arquivo.addAction(abrir_foto)
        menu_arquivo.addAction(menu_abrir_em_janela)
        menu_arquivo.addSeparator()
        menu_arquivo.addAction(menu_abrir_janela)
        menu_arquivo.addMenu(menu_abrir_recentes)
        menu_arquivo.addAction(menu_abrir_file_manager)
        menu_arquivo.addSeparator()
        menu_arquivo.addAction(salvar_foto)
        menu_arquivo.addAction(salvar_foto_como)
        menu_arquivo.addSeparator()
        menu_arquivo.addAction(sair)

        # MENU FILTROS
        filtro_original = QAction("Original", self)
        filtro_original.setShortcut("Ctrl+G")
        filtro_original.triggered.connect(lambda: self.__adicionar_filtro(0))

        filtro_aden = QAction("Aden", self)
        filtro_aden.triggered.connect(lambda: self.__adicionar_filtro(1))

        filtro_clarendon = QAction("Clarendon", self)
        filtro_clarendon.triggered.connect(lambda: self.__adicionar_filtro(2))

        filtro_earlybird = QAction("Earlybird ", self)
        filtro_earlybird.triggered.connect(lambda: self.__adicionar_filtro(3))

        filtro_hudson = QAction("Hudson", self)
        filtro_hudson.triggered.connect(lambda: self.__adicionar_filtro(4))

        filtro_lark = QAction("Lark", self)
        filtro_lark.triggered.connect(lambda: self.__adicionar_filtro(5))

        filtro_lofi = QAction("Lofi", self)
        filtro_lofi.triggered.connect(lambda: self.__adicionar_filtro(6))

        filtro_maven = QAction("Maven", self)
        filtro_maven.triggered.connect(lambda: self.__adicionar_filtro(7))

        filtro_reyes = QAction("Reyes", self)
        filtro_reyes.triggered.connect(lambda: self.__adicionar_filtro(8))

        filtro_valencia = QAction("Valencia", self)
        filtro_valencia.triggered.connect(lambda: self.__adicionar_filtro(9))

        filtro_walden = QAction("Walden", self)
        filtro_walden.triggered.connect(lambda: self.__adicionar_filtro(10))

        filtro_aleatorio = QAction("Filtro aleatório", self)
        filtro_aleatorio.setShortcut("Ctrl+F")
        filtro_aleatorio.setIcon(QIcon(self.__RESOURCES + 'flip-svgrepo-com'))
        filtro_aleatorio.triggered.connect(lambda: self.__adicionar_filtro(random.randint(1, 10)))

        menu_filtros = QMenu("&Filtros", self)
        menu_filtros.setStyleSheet(stylesheet)

        menu_filtros.addAction(filtro_aden)
        menu_filtros.addAction(filtro_clarendon)
        menu_filtros.addAction(filtro_earlybird)
        menu_filtros.addAction(filtro_hudson)
        menu_filtros.addAction(filtro_lark)
        menu_filtros.addAction(filtro_lofi)
        menu_filtros.addAction(filtro_maven)
        menu_filtros.addAction(filtro_reyes)
        menu_filtros.addAction(filtro_valencia)
        menu_filtros.addAction(filtro_walden)

        # MENU EDITAR
        corrigir_iluminacao = QAction("Corrigir iluminação", self)
        corrigir_iluminacao.setIcon(QIcon(self.__RESOURCES + 'brightness-half-svgrepo-com'))
        corrigir_iluminacao.triggered.connect(lambda: self.__corrigir_iluminacao(0))

        self.__corrigir_iluminacao_add = QAction("Aumentar iluminação", self)
        self.__corrigir_iluminacao_add.triggered.connect(lambda: self.__corrigir_iluminacao(1))

        self.__corrigir_iluminacao_rmv = QAction("Diminuir iluminação", self)
        self.__corrigir_iluminacao_rmv.triggered.connect(lambda: self.__corrigir_iluminacao(2))

        self.__corrigir_nitidez_add = QAction("Aumentar nitidez")
        self.__corrigir_nitidez_add.triggered.connect(lambda: self.__corrigir_nitidez(1))

        self.__corrigir_nitidez_rmv = QAction("Diminuir nitidez")
        self.__corrigir_nitidez_rmv.triggered.connect(lambda: self.__corrigir_nitidez(2))

        crop_imagem = QAction("Recortar margens", self)
        crop_imagem.setShortcut("Ctrl+x")
        crop_imagem.setIcon(QIcon(self.__RESOURCES + 'crop-svgrepo-com.svg'))
        crop_imagem.triggered.connect(lambda: self.__crop_margem())

        color_picker = QAction("Seleção de cores", self)
        color_picker.setShortcut("Ctrl+p")
        color_picker.setIcon(QIcon(self.__RESOURCES + 'color-picker-svgrepo-com.svg'))
        color_picker.triggered.connect(lambda: self.exibir_cor_selecionada(self.__viewer.get_posicao_mouse()))

        menu_editar = QMenu("&Editar", self)
        menu_editar.setStyleSheet(stylesheet)
        menu_editar.addAction(corrigir_iluminacao)
        menu_editar.addSeparator()
        menu_editar.addAction(self.__corrigir_iluminacao_add)
        menu_editar.addAction(self.__corrigir_iluminacao_rmv)
        menu_editar.addSeparator()
        menu_editar.addAction(self.__corrigir_nitidez_add)
        menu_editar.addAction(self.__corrigir_nitidez_rmv)
        menu_editar.addSeparator()
        menu_editar.addMenu(menu_filtros)
        menu_editar.addAction(filtro_aleatorio)
        menu_editar.addSeparator()
        menu_editar.addAction(crop_imagem)
        menu_editar.addSeparator()
        menu_editar.addAction(color_picker)
        menu_editar.addSeparator()
        menu_editar.addAction(filtro_original)

        # MENU VISUALIZAR
        centralizar = QAction("Centralizar imagem", self)
        centralizar.setShortcut("Space")
        centralizar.setIcon(QIcon(self.__RESOURCES + 'resize-svgrepo-com.svg'))
        centralizar.triggered.connect(lambda: self.__viewer.centralizar())

        ampliar = QAction("Ampliar a imagem", self)
        ampliar.setShortcut("+")
        ampliar.triggered.connect(lambda: self.__viewer.ampliar())

        reduzir = QAction("Reduzir a imagem", self)
        reduzir.setShortcut("-")
        reduzir.triggered.connect(lambda: self.__viewer.reduzir())

        exibir_diretorio = QAction("Exibir diretorio", self)
        exibir_diretorio.setCheckable(True)
        exibir_diretorio.setChecked(Config().get_config_boolean('editor', 'toolbar_diretorio'))
        exibir_diretorio.triggered.connect(self.__exibir_diretorio)

        fullscreen = QAction("Fullscreen", self)
        fullscreen.setShortcut("f")
        fullscreen.triggered.connect(lambda: self.__full_screen())

        apresentacao_slide = QAction("Apresentação de slides", self)
        apresentacao_slide.setShortcut("f3")
        apresentacao_slide.triggered.connect(lambda: self.__set_slide())

        menu_visualizar = QMenu("&Visualizar", self)
        menu_visualizar.setStyleSheet(stylesheet)
        menu_visualizar.addAction(centralizar)
        menu_visualizar.addSeparator()
        menu_visualizar.addAction(ampliar)
        menu_visualizar.addAction(reduzir)
        menu_visualizar.addSeparator()
        menu_visualizar.addAction(exibir_diretorio)
        menu_visualizar.addSeparator()
        menu_visualizar.addAction(apresentacao_slide)
        menu_visualizar.addAction(fullscreen)

        # MENU IMAGEM
        proxima_imagem = QAction("Proxima", self)
        proxima_imagem.setShortcut("Right")
        proxima_imagem.setIcon(QIcon(self.__RESOURCES + 'arrow-right-svgrepo-com.svg'))
        proxima_imagem.triggered.connect(lambda: self.__mudar_imagem('dir'))

        imagem_anterior = QAction("Anterior", self)
        imagem_anterior.setShortcut("Left")
        imagem_anterior.setIcon(QIcon(self.__RESOURCES + 'arrow-left-svgrepo-com.svg'))
        imagem_anterior.triggered.connect(lambda: self.__mudar_imagem('esq'))

        recarregar_imagem = QAction("Recarregar imagem", self)
        recarregar_imagem.setShortcut("f5")
        recarregar_imagem.setIcon(QIcon(self.__RESOURCES + 'refresh-svgrepo-com.svg'))
        recarregar_imagem.triggered.connect(lambda: self.__recarregar_imagem())

        girar_dir = QAction("Girar em Sentido Horário", self)
        girar_dir.setShortcut("Ctrl+Right")
        girar_dir.setIcon(QIcon(self.__RESOURCES + 'redo-svgrepo-com.svg'))
        girar_dir.triggered.connect(lambda: self.__viewer.rotacionar('dir'))

        girar_esq = QAction("Girar em Sentido Anti-Horário", self)
        girar_esq.setShortcut("Ctrl+Left")
        girar_esq.setIcon(QIcon(self.__RESOURCES + 'undo-svgrepo-com.svg'))
        girar_esq.triggered.connect(lambda: self.__viewer.rotacionar('esq'))

        inverter_v = QAction("Inverter na vertical", self)
        inverter_v.setShortcut("Ctrl+Up")
        inverter_v.setIcon(QIcon(self.__RESOURCES + 'vertical-flip-svgrepo-com.svg'))
        inverter_v.triggered.connect(lambda: self.__viewer.inverter_vertical())

        inverter_h = QAction("Inverter na horizontal", self)
        inverter_h.setShortcut("Ctrl+Down")
        inverter_h.setIcon(QIcon(self.__RESOURCES + 'horizontal-flip-svgrepo-com.svg'))
        inverter_h.triggered.connect(lambda: self.__viewer.inverter_horizontal())

        self.__usar_antialiasing = QAction("Suavizar imagem", self)
        self.__usar_antialiasing.setCheckable(True)
        self.__usar_antialiasing.setChecked(Config().get_config_boolean('editor', 'antialiasing'))
        self.__usar_antialiasing.triggered.connect(lambda: self.__mudar_antialiasing())

        menu_imagem = QMenu("&Imagem", self)
        menu_imagem.setStyleSheet(stylesheet)
        menu_imagem.addAction(proxima_imagem)
        menu_imagem.addAction(imagem_anterior)
        menu_imagem.addSeparator()
        menu_imagem.addAction(recarregar_imagem)
        menu_imagem.addSeparator()
        menu_imagem.addAction(girar_dir)
        menu_imagem.addAction(girar_esq)
        menu_imagem.addSeparator()
        menu_imagem.addAction(inverter_v)
        menu_imagem.addAction(inverter_h)
        menu_imagem.addSeparator()
        menu_imagem.addAction(self.__usar_antialiasing)

        # MENU AJUDA
        sobre = QAction("&Sobre", self)
        sobre.triggered.connect(self.__abrir_info_dialog)

        editar_gimp = QAction("&Abrir com Gimp", self)
        editar_gimp.triggered.connect(self.__editar_gimp)

        menu_ajuda = QMenu("&Ajuda", self)
        menu_ajuda.setStyleSheet(stylesheet)

        menu_ajuda.addAction(sobre)
        menu_ajuda.addSeparator()
        menu_ajuda.addAction(editar_gimp)

        # BARRA DE MENU
        self.menuBar().setStyleSheet(
            f"background-color: {Theme.color_secondary}; color: {Theme.color_text}; padding: 2px;"
        )
        self.menuBar().setAutoFillBackground(True)
        self.menuBar().addMenu(menu_arquivo)
        self.menuBar().addMenu(menu_editar)
        self.menuBar().addMenu(menu_visualizar)
        self.menuBar().addMenu(menu_imagem)
        self.menuBar().addMenu(menu_ajuda)

    def __configurar_tool_bar(self):
        """Configurações das barras de ferramentas"""
        tamanho_icones = QSize(12, 12)

        # Barra de formatação
        self.__diretorio_tool_bar.setStyleSheet(
            "QToolBar {background-color:" + Theme.color_secondary +
            "; border:None;}QToolBar::item{color:" + Theme.color_text +
            ";} QToolBar::item:selected{background-color: " + Theme.color_secondary +
            "; color:" + Theme.color_text + ";}"
        )
        self.__diretorio_tool_bar.setFloatable(False)
        self.__diretorio_tool_bar.setMovable(False)
        self.__diretorio_tool_bar.setIconSize(tamanho_icones)
        self.__diretorio_tool_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.__label_diretorio.setStyleSheet(
            "QLabel {color: " + Theme.color_text + "; font-weight:italic; padding:2px;}"
        )
        self.__label_diretorio.clicked.connect(lambda: self.__mudar_diretorio())
        self.__label_diretorio.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.__label_diretorio.setStatusTip('Carregar diretório anterior')

        acao_diretorio = QAction(QIcon(self.__RESOURCES + 'folder-svgrepo-com.svg'), "&Imagens", self)
        acao_diretorio.setEnabled(False)

        self.__diretorio_tool_bar.addAction(acao_diretorio)
        self.__diretorio_tool_bar.addWidget(self.__label_diretorio)

        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, self.__diretorio_tool_bar)

    def __configurar_status_bar(self):
        self.statusBar().setStyleSheet(
            "background-color: " + Theme.color_secondary +
            "; color:" + Theme.color_text +
            "; padding: 2px; border: None;"
        )
        self.statusBar().setSizeGripEnabled(False)
        self.statusBar().addWidget(self.label_tamanho, 1)
        self.statusBar().addWidget(self.label_cor, 0)
        self.statusBar().addWidget(self.label_cor_nome, 0)
        self.statusBar().addWidget(self.label_zoom, 0)
        self.statusBar().addWidget(self.label_lista, 0)

    def __processar_caminho(self, path) -> str:
        if path == "":
            return QDir.homePath()

        arquivo = ""
        if os.path.isdir(path):
            # lista_dir = sorted([x for x in os.listdir(path) if not x.startswith('.') and x.find('.') == -1])
            lista_files = sorted(
                [x for x in os.listdir(path) if not x.startswith('.') and x.find('.') != -1])

            for item in lista_files:
                if item.split('.')[1] in self.__LISTA_EXTENSOES:
                    arquivo = item
                    break

        return f'{path}{arquivo}'

    def __carregar_imagem(self, caminho: str):
        try:
            path = Path(self.__processar_caminho(caminho))
            dir_path = f"/{'/'.join(path.parts[1:-1])}/"

            if path.exists():
                lista_imagens_raw = [x for x in os.listdir(dir_path) if x.find('.') != -1]
                lista_imagens_processadas = ['.'.join([x.split('.')[0], x.split('.')[1].lower()]) for x in
                                             lista_imagens_raw]
                lista_imagens = []

                for item in lista_imagens_processadas:
                    if item.split('.')[1] in self.__LISTA_EXTENSOES:
                        lista_imagens.append(item)

                # lista_imagens = [x for x in os.listdir(dir_path) if (x.find(".jpg") != -1) or (x.find(".png") != -1)]

                imagem = None
                if path.is_file():
                    imagem = '.'.join([path.parts[-1].split('.')[0], path.parts[-1].split('.')[1].lower()])

                try:
                    lista_numeros = sorted([x for x in lista_imagens if x[0].isdigit()],
                                           key=lambda x: float(x[:-4]))
                except ValueError:
                    lista_numeros = lista_imagens

                lista_letras = sorted([x for x in lista_imagens if x[0].isalpha() or x[0].isascii()], key=str.lower)
                lista_final = []
                lista_final.extend(lista_numeros)

                for elemento in lista_letras:
                    if elemento not in lista_final:
                        lista_final.append(elemento)

                indice = 0
                if imagem is not None:
                    for item in lista_final:
                        if item == imagem:
                            break
                        indice += 1

                # Exibindo a barra de menu inferior
                if len(lista_final) <= 1:
                    self.label_left.setHidden(True)
                    self.label_right.setHidden(True)
                else:
                    self.label_left.setHidden(False)
                    self.label_right.setHidden(False)

                # atualizando variaveis
                self.__info_dir = {
                    "path": dir_path,
                    "indice": indice,
                    "lista": lista_final
                }
                self.setWindowTitle(imagem)
                self.__carregar_info()
                self.__rotacao = 0
                self.__viewer.adicionar_imagem(QPixmap(f'{dir_path}{lista_final[indice]}'))

                Config().set_config('editor', 'caminho', dir_path)

                lista_recentes = Config().get_config('editor', 'recentes').split(',')
                if lista_recentes[0] != "None":
                    lista_recentes.append(f'{dir_path}{lista_final[indice]}')

                    if len(lista_recentes) > 3:
                        Config().set_config('editor', 'recentes', ','.join(lista_recentes[1:]))
                    else:
                        Config().set_config('editor', 'recentes', ','.join(lista_recentes))
                else:
                    Config().set_config('editor', 'recentes', f'{dir_path}{lista_final[indice]}')

        except IndexError:
            pass

    def __carregar_info(self):
        try:
            lista = self.__info_dir['lista']
            imagem = lista[self.__info_dir['indice']]
            caminho = f"{self.__info_dir['path']}"

            if len(lista) <= 1:
                indice_calculado = 1
            else:
                indice_calculado = self.__info_dir['indice'] + 1

            largura, altura = Image.open(f"{caminho}{imagem}").size

            caminho_processado = caminho
            caminho_split = caminho.split('/')[:-1]
            tamanho_caminho = 4
            if len(caminho_split) >= tamanho_caminho:
                caminho_processado = "..." + "/".join(caminho_split[len(caminho_split) - tamanho_caminho:])
            self.__label_diretorio.setText(caminho_processado)

            modificado = datetime.fromtimestamp(os.stat(f"{caminho}{imagem}").st_ctime)
            criado = datetime.fromtimestamp(os.stat(f"{caminho}{imagem}").st_mtime)

            self.label_tamanho.setText(
                str(largura) + "  x " + str(altura) + " pixels  " +
                str(int(os.path.getsize(f"{caminho}{imagem}") / 1024)) + "kB  " +
                f'em {min(modificado, criado).strftime("%d/%m/%Y")}'
            )

            self.label_lista.setText(str(indice_calculado) + " / " + str(len(lista)))
        except IndexError:
            pass

    def __mudar_imagem(self, direcao: str):
        try:
            if direcao == 'dir':
                self.__info_dir['indice'] += 1
            else:
                self.__info_dir['indice'] -= 1

            indice = self.__info_dir['indice']
            lista = self.__info_dir['lista']
            caminho = f"{self.__info_dir['path']}"

            if indice >= len(self.__info_dir['lista']):
                proxima = lista[0]
                indice = 0
            elif indice < 0:
                proxima = lista[-1]
                indice = len(lista) - 1
            else:
                proxima = lista[indice]

            self.__viewer.adicionar_imagem(QPixmap(f'{caminho}{proxima}'))
            self.__info_dir['indice'] = indice
            self.setWindowTitle(proxima)
            self.__carregar_info()
        except IndexError:
            pass

    def __mudar_diretorio(self):
        path = Path(self.__info_dir['path'])
        dir_path = f"/{'/'.join(path.parts[1:-1])}/"
        Config().set_config('editor', 'caminho', dir_path)

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir foto",
            dir_path,
            f'Imagens ({"*."+", *.".join(self.__LISTA_EXTENSOES)})'
        )

        self.__carregar_imagem(filename)

    def __abrir_imagem(self):

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir foto",
            Config().get_config('editor', 'caminho'),
            f'Imagens ({"*."+", *.".join(self.__LISTA_EXTENSOES)})'
        )

        if filename != "":
            Config().set_config('editor', 'caminho', filename)
            self.__carregar_imagem(filename)

    def __salvar_imagem(self):
        filename = f'{self.__info_dir["path"]}{self.__info_dir["lista"][self.__info_dir["indice"]]}'

        if filename != "":
            self.__viewer.m_pixmap.save(filename, quality=100)
            self.__carregar_imagem(filename)

    def __salvar_imagem_como(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar foto",
            f'{self.__info_dir["path"]}',
            f'Imagens ({"*."+", *.".join(self.__LISTA_EXTENSOES)})'
        )
        if filename != "":
            self.__viewer.m_pixmap.save(filename, quality=100)
            self.__carregar_imagem(filename)

    def __recarregar_imagem(self):
        filename = f'{self.__info_dir["path"]}{self.__info_dir["lista"][self.__info_dir["indice"]]}'
        self.__carregar_imagem(filename)

    def __abrir_info_dialog(self):
        SobreDialog(self.__VERSAO, Theme(), self).exec()

    def __exibir_diretorio(self):
        config = Config().get_config_boolean('editor', 'toolbar_diretorio')
        if config:
            self.__diretorio_tool_bar.setVisible(False)
        else:
            self.__diretorio_tool_bar.setVisible(True)

        Config().set_config('editor', 'toolbar_diretorio', str(self.__diretorio_tool_bar.isVisible()))

    def __adicionar_filtro(self, fid: int):
        ext = self.__info_dir["lista"][self.__info_dir["indice"]].split('.')[1]
        im = Image.open(f'{self.__info_dir["path"]}{self.__info_dir["lista"][self.__info_dir["indice"]]}')
        filtro = None

        if fid == 0:
            self.__recarregar_imagem()
            self.setStatusTip("Filtro original")
        if fid == 1:
            filtro = pilgram.aden(im)
            self.setStatusTip("Filtro aden")
        elif fid == 2:
            filtro = pilgram.clarendon(im)
            self.setStatusTip("Filtro clarendon")
        elif fid == 3:
            filtro = pilgram.earlybird(im)
            self.setStatusTip("Filtro earlybird")
        elif fid == 4:
            filtro = pilgram.hudson(im)
            self.setStatusTip("Filtro hudson")
        elif fid == 5:
            filtro = pilgram.lark(im)
            self.setStatusTip("Filtro lark")
        elif fid == 6:
            filtro = pilgram.lofi(im)
            self.setStatusTip("Filtro lofi")
        elif fid == 7:
            filtro = pilgram.maven(im)
            self.setStatusTip("Filtro maven")
        elif fid == 8:
            filtro = pilgram.reyes(im)
            self.setStatusTip("Filtro reyes")
        elif fid == 9:
            filtro = pilgram.valencia(im)
            self.setStatusTip("Filtro valencia")
        elif fid == 10:
            filtro = pilgram.walden(im)
            self.setStatusTip("Filtro walden")

        if filtro is not None:
            filename = f'{self.__CAMINHO_HOME}/cropped.{ext}'
            filtro.save(filename, quality=100)

            self.__viewer.adicionar_imagem(QPixmap(filename))

    def __mudar_antialiasing(self):
        config = Config()

        if config.get_config_boolean('editor', 'antialiasing'):
            config.set_config('editor', 'antialiasing', False)
            self.__usar_antialiasing.setChecked(False)
            self.__viewer.mudar_antialiasing(False)
            self.__recarregar_imagem()
        else:
            config.set_config('editor', 'antialiasing', True)
            self.__usar_antialiasing.setChecked(True)
            self.__viewer.mudar_antialiasing(True)
            self.__recarregar_imagem()

    def __full_screen(self):
        if self.windowState() and Qt.WindowState.WindowFullScreen:
            self.showNormal()
        else:
            self.showFullScreen()

        self.__viewer.centralizar()

    def __slide_show(self):
        self.__mudar_imagem('dir')
        self.__timer.run()

    def __set_slide(self):
        if self.__timer.is_alive():
            self.__timer.cancel()
        else:
            try:
                self.__timer.start()
            except RuntimeError:
                self.__timer = Timer(self.__timer_interval, self.__slide_show)
                self.__timer.start()

    def cancelar_timer(self):
        self.__timer.cancel()

    @staticmethod
    def __verifica_igualdade_pixels(ant, atual, fator):
        return ((ant[0] == atual[0]) and (ant[1] == atual[1]) and (ant[2] == atual[2])) or \
            ((abs(ant[0] - atual[0]) <= fator) and (abs(ant[1] - atual[1]) <= fator) and (
                abs(ant[2] - atual[2])) <= fator)

    def __cut_image(self, im: Image, fator=3) -> (int, int, int, int):
        width, height = im.size

        metade_vertical = floor(height / 2)
        metade_horizontal = floor(width / 2)

        x1 = 0
        x2 = 0
        x3 = 0
        x4 = 0

        # START
        col = 1
        while col < floor(width / 2):
            pixel_anterior = im.getpixel((col - 1, metade_vertical))
            pixel_atual = im.getpixel((col, metade_vertical))

            if self.__verifica_igualdade_pixels(pixel_anterior, pixel_atual, fator):
                x1 += 1
            else:
                x1 += 1
                break

            col += 1

        # END
        col = width - 2
        while col > floor(width / 2):
            pixel_anterior = im.getpixel((col + 1, metade_vertical))
            pixel_atual = im.getpixel((col, metade_vertical))

            if self.__verifica_igualdade_pixels(pixel_anterior, pixel_atual, fator):
                x2 += 1
            else:
                x2 += 1
                break

            col -= 1

        # TOP
        lin = 1
        while lin < floor(height / 2):
            pixel_anterior = im.getpixel((metade_horizontal, lin - 1))
            pixel_atual = im.getpixel((metade_horizontal, lin))

            if self.__verifica_igualdade_pixels(pixel_anterior, pixel_atual, fator):
                x3 += 1
            else:
                x3 += 1
                break

            lin += 1

        # BOT
        lin = height - 2
        while lin > floor(height / 2):
            pixel_anterior = im.getpixel((metade_horizontal, lin + 1))
            pixel_atual = im.getpixel((metade_horizontal, lin))

            if self.__verifica_igualdade_pixels(pixel_anterior, pixel_atual, fator):
                x4 += 1
            else:
                x4 += 1
                break

            lin -= 1

        return x1, width - x2, x3, height - x4

    def __crop_margem(self):
        ext = self.__info_dir["lista"][self.__info_dir["indice"]].split('.')[1]
        im = Image.open(f'{self.__info_dir["path"]}{self.__info_dir["lista"][self.__info_dir["indice"]]}')

        x, w, y, h = self.__cut_image(im)

        im1 = im.crop((x, y, w, h))
        filename = f'{self.__CAMINHO_HOME}/cropped.{ext}'
        im1.save(filename, quality=100)

        self.__viewer.adicionar_imagem(QPixmap(filename))

    def __corrigir_iluminacao(self, valor: int):
        ext = self.__info_dir["lista"][self.__info_dir["indice"]].split('.')[1]

        im = Image.open(f'{self.__info_dir["path"]}{self.__info_dir["lista"][self.__info_dir["indice"]]}')

        if valor == 0:
            self.__enhance += .4
        elif valor == 1 and self.__enhance < 2:
            self.__enhance += .4
        elif valor == 2 and self.__enhance > 0:
            self.__enhance -= .4

        self.__corrigir_iluminacao_add.setEnabled(False if self.__enhance >= 2 else True)
        self.__corrigir_iluminacao_rmv.setEnabled(False if self.__enhance <= 0 else True)

        im1 = ImageEnhance.Color(im).enhance(self.__enhance)

        filename = f'{self.__CAMINHO_HOME}/corrigida.{ext}'

        im1.save(filename, quality=100)
        self.__viewer.adicionar_imagem(QPixmap(filename))

    def __corrigir_nitidez(self, valor: int):
        ext = self.__info_dir["lista"][self.__info_dir["indice"]].split('.')[1]
        im = Image.open(f'{self.__info_dir["path"]}{self.__info_dir["lista"][self.__info_dir["indice"]]}')

        if valor == 1 and self.__nitidez < 2:
            self.__nitidez += .4
        elif valor == 2 and self.__nitidez > 0:
            self.__nitidez -= .4

        self.__corrigir_nitidez_add.setEnabled(False if self.__nitidez >= 2 else True)
        self.__corrigir_nitidez_rmv.setEnabled(False if self.__nitidez <= 0 else True)

        im1 = ImageEnhance.Sharpness(im).enhance(self.__nitidez)

        filename = f'{self.__CAMINHO_HOME}/corrigida.{ext}'
        im1.save(filename, quality=100)
        self.__viewer.adicionar_imagem(QPixmap(filename))

    def exibir_cor_selecionada(self, pos: ()):
        if self.__viewer.m_pixmap:
            r, g, b, _ = pos  # self.__viewer.get_posicao_mouse()
            cor = '#{:02X}{:02X}{:02X}'.format(r, g, b)

            self.label_cor.setText('●')
            self.label_cor.setStyleSheet(
                "QLabel {color: " + cor + "; font-weight:bold; padding:0px;}"
            )

            self.label_cor_nome.setText(cor)
            self.label_cor_nome.setStyleSheet(
                "QLabel {color: " + Theme.color_text + "; font-weight:italic; padding:0px;}"
            )

    def __copiar_cor_para_transferencia(self):
        self.__app.clipboard().setText(self.label_cor_nome.text())

    @staticmethod
    def __abrir_nova_janela(caminho: str = ""):
        if "__main__.py" in os.listdir(os.getcwd()):
            os.system(f'cd {os.getcwd()}; python __main__.py "{caminho}";cd;')
        else:
            if platform.system() == "Windows":
                os.system(f'{os.getcwd()}/Do Image Viewer.exe "{caminho}"')
            else:
                os.system(f'cd {os.getcwd()}; ./Do\\ Image\\ Viewer "{caminho}";cd;')

    def __abrir_foto_nova_janela(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir foto",
            Config().get_config('editor', 'caminho'),
            f'Imagens ({"*."+", *.".join(self.__LISTA_EXTENSOES)})'
        )

        if filename != "":
            self.__abrir_nova_janela(filename)

    def __abrir_file_manager(self):
        show_in_file_manager(f'{self.__info_dir["path"]}{self.__info_dir["lista"][self.__info_dir["indice"]]}')

    def __editar_gimp(self):
        try:
            Popen(['gimp', f'{self.__info_dir["path"]}{self.__info_dir["lista"][self.__info_dir["indice"]]}'])
        except IndexError:
            QMessageBox.critical(self, "Erro", "Nenhuma imagem carregada.")
