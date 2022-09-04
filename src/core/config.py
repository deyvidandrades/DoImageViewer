"""
Classe responsável pelo gerenciamento de configurações '.ini' do programa
"""
import os
from configparser import ConfigParser


class Config:
    """
    Classe de configurações
    """
    __CAMINHO = os.getcwd() + '/config.ini'

    def __init__(self) -> None:
        super().__init__()
        self.__config = ConfigParser()
        self.__config.read(self.__CAMINHO)

    def get_config(self, secao: str = None, opcao: str = None) -> str:
        """
        Método de leitura das configurações
        :param secao: .ini section
        :param opcao: .ini option
        :return: .ini value
        """
        if secao is not None:
            return self.__config.get(secao, opcao)
        return ''

    def get_config_boolean(self, secao: str = None, opcao: str = None) -> bool:
        """
        Método de leitura das configurações booleanas
        :param secao: .ini section
        :param opcao: .ini option
        :return: '.ini' bool value
        """
        if secao is not None:
            return self.__config.getboolean(secao, opcao)
        return False

    def get_window_info(self, opcao: str = None) -> (int, int):
        config = self.__config.get('window', opcao).split(',')

        return int(config[0]), int(config[1])

    def set_config(self, secao: str = None, opcao: str = None, valor: any = None) -> None:
        """
        Salvar as configurações no arquivo .ini
        :param secao: .ini section
        :param opcao: .ini option
        :param valor: .ini value
        :return: None
        """
        self.__config.set(secao, opcao, str(valor))
        with open(self.__CAMINHO, 'w') as configfile:
            self.__config.write(configfile, True)
