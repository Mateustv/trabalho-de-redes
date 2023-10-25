import socket
import wave
import os
from threading import Thread

class Server():
    def __init__(self, porta=2635, max_conexoes=3):
        self.__ip = None
        self.__porta_servidor = porta
        self.__max_conexoes = max_conexoes
        self.__socket_servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__dict_dispositivos_sockets = {}
        self.__dispositivos_conectados = []
    def start_server(self):
        self.__obter_ip()
        self.__socket_servidor.bind((self.__ip, self.__porta_servidor))
        self.__socket_servidor.listen(self.__max_conexoes)
        print("Iniciando servidor. Aguardando novas conexões\n ... ")
        print(self.__ip)
        self.__run_server_for_listen()
    def __obter_ip(self):
        try:
            # Cria um socket UDP
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            # Conecta o socket a um servidor DNS
            sock.connect(("8.8.8.8", 80))

            # Obtém o endereço IP do socket
            ip = sock.getsockname()[0]

            # Fecha o socket
            sock.close()

            self.__ip = ip
        except socket.error:
            return "Não foi possível obter o endereço IP"

    def __send_dados(self, socket_cliente: socket, msg: bytes):
        print(f"Mandando a mensagem : {msg.decode()} pra {socket_cliente}")
        socket_cliente.send(msg)

    def __send_lista_de_musica(self, socket_cliente):
        pasta = os.listdir("./Biblioteca")
        musicas = []
        for arquivo in pasta:
            if arquivo.endswith(".wav"):
                # Remove a extensão do nome da música
                nome_musica = os.path.splitext(arquivo)[0]
                musicas.append(nome_musica)
        teladeMusicas = ''
        for musica in musicas:
            teladeMusicas += musica + "\n"
        #teladeMusicas
        self.__send_dados(socket_cliente, teladeMusicas.encode())

    def __remover_dipostivos_conectados(self, socket_cliente, msg, endereco_cliente, e=Exception()):
        print(f"{msg} {endereco_cliente}")
        socket_cliente.close()
        for dispositivo in self.__dispositivos_conectados:
            if len(dispositivo) == 3:
                endereco_cliente_1, enderecos_dos_clientes, musica = dispositivo
                if endereco_cliente[0] == endereco_cliente_1 and endereco_cliente[1] == enderecos_dos_clientes:
                    self.__dispositivos_conectados.remove(dispositivo)
            else:
                endereco_cliente_1, enderecos_dos_clientes = dispositivo
                if endereco_cliente[0] == endereco_cliente_1 and endereco_cliente[1] == enderecos_dos_clientes:
                    self.__dispositivos_conectados.remove(dispositivo)

    def __check_musica_existe(self, musica_escolhida):
        musicas = os.listdir("./Biblioteca")
        print(f'lista das musicas {musicas}')
        for (musica) in (musicas):
            nome_musica, extensao = os.path.splitext(musica)
            if musica_escolhida.lower() == nome_musica.lower():
                print("Musica encotrada")
                musica_escolhida = musica
                return True, musica_escolhida
        return False, musica_escolhida

    def __baixar_musica_para_o_cliente(self, musica_escolhida, socket_cliente):
        caminho_da_musica = "./Biblioteca/" + musica_escolhida
        wf = wave.open(caminho_da_musica, 'rb')

        chunk = 44100 * 2 * 30

        print(f"chunk = {chunk}")
        # informa que onde começa o download
        self.__send_dados(socket_cliente, b"track_data_start")
        dataMsc = 1
        while dataMsc:
            # Qntde de data (30 segundos) sendo lidas e enviadas
            dataMsc = wf.readframes(chunk)
            print(f"Mandando 30 segundos de musica da musica: {musica_escolhida}")
            socket_cliente.send(dataMsc)
        self.__send_dados(socket_cliente, b"track_data_end")
        print(f'A musica {musica_escolhida} foi enviada')
    def __cliente_thread(self, socket_cliente, endereco_cliente):
        print(f"<{endereco_cliente} conectado>")

        while True:
            try:
                valor_recebido_do_cliente = (socket_cliente.recv(1024).decode())
                valor_recebido_em_array = valor_recebido_do_cliente.split(" ")
                if not valor_recebido_do_cliente:
                    raise Exception
                print(f"Recebido de {endereco_cliente} : {valor_recebido_do_cliente}")
                if valor_recebido_do_cliente == "lista" or valor_recebido_do_cliente == "7":
                    self.__send_lista_de_musica(socket_cliente)
                elif valor_recebido_em_array[0] == 'download':
                    musica_existe_bool, nome_musica = self.__check_musica_existe(valor_recebido_em_array[1])
                    if not musica_existe_bool:
                        self.__send_dados(socket_cliente, f"Musica '{nome_musica}' não encontrada. Va em lista para ver as musicas disponiveis".encode())
                        continue
                    try:
                        self.__baixar_musica_para_o_cliente(nome_musica, socket_cliente)
                    except ConnectionResetError:
                        print(f"Sua conexao foi reniciada {endereco_cliente}")
                        socket_cliente.close()
                        break
                    except TimeoutError:
                        print(f"Timeout erro, fechando sua conexao para {endereco_cliente}")
                        socket_cliente.close()
                        break
            except ConnectionResetError:
                self.__remover_dipostivos_conectados(socket_cliente, "Conexao foi reniciada", endereco_cliente)
                break
            except Exception as e:
                self.__remover_dipostivos_conectados(socket_cliente, "Ocorreu um erro", endereco_cliente, e)
                break
        return

    def __run_server_for_listen(self):
        while True:
            try:
                (socket_cliente, endereco_cliente) = self.__socket_servidor.accept()
                self.__dict_dispositivos_sockets[endereco_cliente[0]] = socket_cliente
                self.__dispositivos_conectados.append(
                    [endereco_cliente[0], endereco_cliente[1]])
            except socket.timeout:
                print(f"Servidor: Desligando thread de escuta")
                break
            thread_server = Thread(target=self.__cliente_thread, args=(socket_cliente,endereco_cliente), daemon=True)
            thread_server.start()


test = Server()
test.start_server()