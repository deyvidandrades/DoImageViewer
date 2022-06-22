import os
from pathlib import Path
from subprocess import Popen

from PIL import Image
from PyQt6.QtCore import QDir, Qt, QSize, QEvent
from PyQt6.QtGui import QIcon, QPixmap, QCursor, QAction
from PyQt6.QtWidgets import QMainWindow, QMenu, QLabel, QHBoxLayout, QWidget, QFileDialog, QApplication, QToolBar, \
    QSizePolicy

from src.core.config import Config
from src.core.widgets import ImageViewer, QLabelClick, SobreDialog


class DoImageViewer(QMainWindow):
    __CAMINHO = QDir.homePath()
    __BACKGROUND_COLOR = '#1b2224'  # f0f0f0
    __RESOURCES = os.getcwd() + "/src/res/"

    def __init__(self, app: QApplication, caminho: str = ""):
        super().__init__()
        # carregar configurações
        config = Config()
        if config.get_config('editor', 'caminho') == "\"\"":
            config.set_config('editor', 'caminho', QDir.homePath() + '/')

        # widget da aplicação
        self.__app = app

        # configurações da tela
        self.setStyleSheet("QMainWindow {background-color: " + self.__BACKGROUND_COLOR + ";color: #f0f0f0;}")
        self.setWindowIcon(QIcon(QPixmap(self.__RESOURCES + 'image-svgrepo-com.svg')))
        self.setWindowTitle("Do Image Viewer v2.0")
        self.setAutoFillBackground(True)

        tela = self.__app.primaryScreen().size()
        self.resize(int(tela.width() * .45), int(tela.height() * .9))

        # variáveis de controle
        self.__viewer = ImageViewer(parent=self)
        self.__caminho = caminho
        self.__diretorio_tool_bar = QToolBar("Diretorio", self)
        self.__diretorio_tool_bar.setVisible(config.get_config_boolean('editor', 'toolbar_diretorio'))
        self.tamanho_icones = QSize(24, 24)

        # labels
        self.label_tamanho = QLabel("")
        self.label_lista = QLabel("Nenhuma foto carregada")
        self.label_zoom = QLabel("")
        self.__label_diretorio = QLabelClick(self.__CAMINHO)

        # configuração do layout principal
        self.__layout_principal = QHBoxLayout()
        self.__layout_principal.setContentsMargins(5, 0, 5, 0)

        self.__centralWidget = QWidget(self)
        self.setCentralWidget(self.__centralWidget)
        self.__centralWidget.setLayout(self.__layout_principal)

        # configuração da interface
        self.__configurar_gui()
        self.__configurar_menu()
        self.__configurar_tool_bar()
        self.__configurar_status_bar()

        self.__carregar_imagem()
        self.setWindowTitle("Do Image Viewer v2.0.4")

    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            if event.oldState() and Qt.WindowState.WindowMinimized:
                self.__viewer.centralizar()
            elif event.oldState() == Qt.WindowState.WindowNoState or \
                    self.windowState() == Qt.WindowState.WindowMaximized:
                self.__viewer.centralizar()

    def __configurar_gui(self):
        self.label_left = QLabelClick()
        self.label_left.setPixmap(QPixmap(self.__RESOURCES + 'left-svgrepo-com.svg').scaled(self.tamanho_icones))
        self.label_left.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.label_left.clicked.connect(lambda: self.__mudar_imagem('esq'))
        self.label_left.setHidden(True)
        self.__layout_principal.addWidget(self.label_left)

        self.__layout_principal.addWidget(self.__viewer, 1)

        self.label_right = QLabelClick()
        self.label_right.setPixmap(QPixmap(self.__RESOURCES + 'right-svgrepo-com.svg').scaled(self.tamanho_icones))
        self.label_right.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.label_right.clicked.connect(lambda: self.__mudar_imagem('dir'))
        self.label_right.setHidden(True)
        self.__layout_principal.addWidget(self.label_right)

    # noinspection PyUnresolvedReferences
    def __configurar_menu(self):
        # MENU ARQUIVO
        abrir_foto = QAction("&Abrir", self)
        abrir_foto.setShortcut("Ctrl+O")
        abrir_foto.triggered.connect(self.__abrir_imagem)

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
        menu_arquivo.setStyleSheet(
            """QMenu {background-color:#263033;} QMenu::item{color:#fafafa;} 
            QMenu::item:selected {background-color: #1D63D1; color:#fafafa;}"""
        )
        menu_arquivo.addAction(abrir_foto)
        menu_arquivo.addSeparator()
        menu_arquivo.addAction(salvar_foto)
        menu_arquivo.addAction(salvar_foto_como)
        menu_arquivo.addSeparator()
        menu_arquivo.addAction(sair)

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

        menu_visualizar = QMenu("&Visualizar", self)
        menu_visualizar.setStyleSheet(
            """QMenu {background-color:#263033;} QMenu::item{color:#fafafa;} 
            QMenu::item:selected {background-color: #1D63D1; color:#fafafa;}"""
        )
        menu_visualizar.addAction(centralizar)
        menu_visualizar.addSeparator()
        menu_visualizar.addAction(ampliar)
        menu_visualizar.addAction(reduzir)
        menu_visualizar.addSeparator()
        menu_visualizar.addAction(exibir_diretorio)

        # MENU IMAGEM
        proxima_imagem = QAction("Proxima", self)
        proxima_imagem.setShortcut("Right")
        proxima_imagem.setIcon(QIcon(self.__RESOURCES + 'arrow-right-svgrepo-com.svg'))
        proxima_imagem.triggered.connect(lambda: self.__mudar_imagem('dir'))

        imagem_anterior = QAction("Anterior", self)
        imagem_anterior.setShortcut("Left")
        imagem_anterior.setIcon(QIcon(self.__RESOURCES + 'arrow-left-svgrepo-com.svg'))
        imagem_anterior.triggered.connect(lambda: self.__mudar_imagem('esq'))

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

        menu_imagem = QMenu("&Imagem", self)
        menu_imagem.setStyleSheet(
            """QMenu {background-color:#263033;} QMenu::item{color:#fafafa;} 
            QMenu::item:selected {background-color: #1D63D1; color:#fafafa;}"""
        )
        menu_imagem.addAction(proxima_imagem)
        menu_imagem.addAction(imagem_anterior)
        menu_imagem.addSeparator()
        menu_imagem.addAction(girar_dir)
        menu_imagem.addAction(girar_esq)
        menu_imagem.addSeparator()
        menu_imagem.addAction(inverter_v)
        menu_imagem.addAction(inverter_h)
        menu_imagem.addSeparator()

        # MENU AJUDA
        sobre = QAction("&Sobre", self)
        sobre.triggered.connect(self.__abrir_info_dialog)

        editar_gimp = QAction("&AEditar com Gimp", self)
        editar_gimp.triggered.connect(self.__editar_gimp)

        menu_ajuda = QMenu("&Ajuda", self)
        menu_ajuda.setStyleSheet(
            """QMenu {background-color:#263033;} QMenu::item{color:#fafafa;} 
            QMenu::item:selected {background-color: #1D63D1; color:#fafafa;}"""
        )

        menu_ajuda.addAction(sobre)
        menu_ajuda.addAction(editar_gimp)

        # BARRA DE MENU
        self.menuBar().setStyleSheet("background-color: #263033; color: #f6f6f6; padding: 2px;")
        self.menuBar().setAutoFillBackground(True)
        self.menuBar().addMenu(menu_arquivo)
        self.menuBar().addMenu(menu_visualizar)
        self.menuBar().addMenu(menu_imagem)
        self.menuBar().addMenu(menu_ajuda)

    def __configurar_tool_bar(self):
        """Configurações das barras de ferramentas"""
        tamanho_icones = QSize(12, 12)

        # Barra de formatação
        self.__diretorio_tool_bar.setStyleSheet(
            """
            QToolBar {background-color:#263033; border:None;} QToolBar::item{color:#fafafa;} QToolBar::item:selected 
            {background-color: #1D63D1; color:#fafafa;}
            """
        )
        self.__diretorio_tool_bar.setFloatable(False)
        self.__diretorio_tool_bar.setMovable(False)
        self.__diretorio_tool_bar.setIconSize(tamanho_icones)
        self.__diretorio_tool_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.__label_diretorio.setStyleSheet("""QLabel {color: #fafafa; font-weight:italic; padding:2px;}""")
        self.__label_diretorio.clicked.connect(lambda: self.__mudar_diretorio())
        self.__label_diretorio.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.__label_diretorio.setStatusTip('Carregar diretório anterior')

        acao_diretorio = QAction(QIcon(self.__RESOURCES + 'folder-svgrepo-com.svg'), "&Imagens", self)
        acao_diretorio.setEnabled(False)

        self.__diretorio_tool_bar.addAction(acao_diretorio)
        self.__diretorio_tool_bar.addWidget(self.__label_diretorio)

        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, self.__diretorio_tool_bar)

    def __configurar_status_bar(self):
        self.statusBar().setStyleSheet("background-color: #263033; color:#f6f6f6; padding: 2px; border: None;")
        self.statusBar().setSizeGripEnabled(False)
        self.statusBar().addWidget(self.label_tamanho, 1)
        self.statusBar().addWidget(self.label_zoom, 0)
        self.statusBar().addWidget(self.label_lista, 0)

    def __carregar_imagem(self):
        try:
            path = Path(self.__caminho)
            dir_path = f"/{'/'.join(path.parts[1:-1])}/"

            if path.exists():
                lista_imagens = [x for x in os.listdir(dir_path) if (x.find(".jpg") != -1) or (x.find(".png") != -1)]

                imagem = None
                if path.is_file():
                    imagem = path.parts[-1]

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

            self.__label_diretorio.setText(caminho)

            self.label_tamanho.setText(
                str(largura) + "  x " + str(altura) + " pixels  " +
                str(int(os.path.getsize(f"{caminho}{imagem}") / 1024)) + "kB"
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
            "Imagens (*.jpg *.jpeg *.png)"
        )

        self.__caminho = filename
        self.__carregar_imagem()

    def __abrir_imagem(self):

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir foto",
            Config().get_config('editor', 'caminho'),
            "Imagens (*.jpg *.jpeg *.png)"
        )

        Config().set_config('editor', 'caminho', filename)
        self.__caminho = filename
        self.__carregar_imagem()

    def __salvar_imagem(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar foto",
            self.__info_dir['path'],
            "Imagens (*.jpg *.jpeg *.png)",
            self.windowTitle()
        )
        if filename != "":
            self.__viewer.m_pixmap.save(filename)
            self.__caminho =filename
            self.__carregar_imagem()

    def __salvar_imagem_como(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar foto",
            self.__CAMINHO,
            "Imagens (*.jpg *.jpeg *.png)"
        )
        if filename != "":
            self.__viewer.m_pixmap.save(filename)
            self.__caminho =filename
            self.__carregar_imagem()

    def __abrir_info_dialog(self):
        SobreDialog(self).exec()

    def __exibir_diretorio(self):
        config = Config().get_config_boolean('editor', 'toolbar_diretorio')
        if config:
            self.__diretorio_tool_bar.setVisible(False)
        else:
            self.__diretorio_tool_bar.setVisible(True)

        Config().set_config('editor', 'toolbar_diretorio', str(self.__diretorio_tool_bar.isVisible()))

    def __editar_gimp(self):
        Popen(['gimp', f'{self.__info_dir["path"]}{self.__info_dir["lista"][self.__info_dir["indice"]]}'])
