
## Importando as Bibliotecas necessárias
import cv2
import mediapipe as mp
import numpy as np
import math
import time

## Configurações de exibição da câmera e do tabuleiro

LARGURA_CAMERA = 1280
ALTURA_CAMERA = 720
TAMANHO_TABULEIRO = 450
X_TABULEIRO = (LARGURA_CAMERA-TAMANHO_TABULEIRO)//2
Y_TABULEIRO = (ALTURA_CAMERA - TAMANHO_TABULEIRO)// 2
TAMANHO_CELULA = TAMANHO_TABULEIRO//3
DISTANCIA_PINCA = 40
TEMPO_ENTRE_JOGADAS = 0.8

## Definindo funções auxiliares

def verificar_vencedor(tabuleiro):
    """
    Verifica se X ou O venceu.

    Retorno:
        "X"     -> jogador X venceu
        "O"     -> jogador O venceu
        "EMPATE" -> tabuleiro cheio
        None    -> jogo ainda continua

    acho que fiz essa função de uma forma bem feia, mas funciona. Se alguém tiver uma ideia melhor, fica à vontade pra mexer =) 
    """

    # Verificando as linhas
    for linha in range(3):
        if (tabuleiro[linha][0] == tabuleiro[linha][1] == tabuleiro[linha][2] != ""):
            return tabuleiro[linha][0]

    # Verificando as colunas
    for coluna in range(3):
        if (tabuleiro[0][coluna] == tabuleiro[1][coluna] == tabuleiro[2][coluna]!= ""):
            return tabuleiro[0][coluna]

    # Verificando a diagonal principal
    if (tabuleiro[0][0] == tabuleiro[1][1] == tabuleiro[2][2] != ""):
        return tabuleiro[0][0]

    # Verificando a diagonal secundária
    if (tabuleiro[0][2] == tabuleiro[1][1] == tabuleiro[2][0] != ""):
        return tabuleiro[0][2]

    # Verificando empate
    tabuleiro_cheio = all(tabuleiro[linha][coluna] != "" for linha in range(3) for coluna in range(3))
    if tabuleiro_cheio:
        return "EMPATE"
    else:
        return None


def desenhar_tabuleiro(frame, tabuleiro):
    """
    Desenha o tabuleiro virtual e os símbolos X e O sobre a câmera.

    da pra trocar essa parte por uma imagem de X e uma imagem de O, acho que fica até melhor mas tava com preguiça de mexer com arquivos de imagem, então fiz assim mesmo. Se alguém quiser melhorar, fique à vontade =)
    """

    overlay = frame.copy()

    # Fundo semitransparente
    cv2.rectangle(overlay, (X_TABULEIRO, Y_TABULEIRO), (X_TABULEIRO + TAMANHO_TABULEIRO, Y_TABULEIRO + TAMANHO_TABULEIRO), (30, 30, 30), -1)
    frame = cv2.addWeighted(overlay, 0.35, frame, 0.65, 0)

    # Linhas verticais
    for coluna in range(1, 3):
        x = X_TABULEIRO + coluna * TAMANHO_CELULA
        cv2.line(frame, (x, Y_TABULEIRO), (x, Y_TABULEIRO + TAMANHO_TABULEIRO), (255, 255, 255), 4)

    # Linhas horizontais
    for linha in range(1, 3):
        y = Y_TABULEIRO + linha * TAMANHO_CELULA
        cv2.line(frame, (X_TABULEIRO, y), (X_TABULEIRO + TAMANHO_TABULEIRO, y), (255, 255, 255), 4)

    # Borda externa
    cv2.rectangle(frame, (X_TABULEIRO, Y_TABULEIRO), (X_TABULEIRO + TAMANHO_TABULEIRO, Y_TABULEIRO + TAMANHO_TABULEIRO), (255, 255, 255), 4)

    # Desenhando os símbolos
    for linha in range(3):
        for coluna in range(3):
            simbolo = tabuleiro[linha][coluna]
            if simbolo == "":
                continue
            centro_x = X_TABULEIRO + coluna * TAMANHO_CELULA + TAMANHO_CELULA // 2
            centro_y = Y_TABULEIRO + linha * TAMANHO_CELULA + TAMANHO_CELULA // 2
            if simbolo == "X":
                margem = 45
                cv2.line(frame, (centro_x - margem, centro_y - margem), (centro_x + margem, centro_y + margem), (255, 100, 100), 8)
                cv2.line(frame, (centro_x + margem, centro_y - margem), (centro_x - margem, centro_y + margem), (255, 100, 100), 8)
            elif simbolo == "O":
                cv2.circle(frame, (centro_x, centro_y), 50, (100, 100, 255), 8)
    return frame


def descobrir_celula(x, y):
    """
    Descobre a linha e a coluna correspondentes à posição do cursor.

    Retorna:
        (linha, coluna), caso o cursor esteja dentro do tabuleiro.
        None, caso esteja fora.
    """

    dentro_horizontal = X_TABULEIRO <= x < X_TABULEIRO + TAMANHO_TABULEIRO
    dentro_vertical = Y_TABULEIRO <= y < Y_TABULEIRO + TAMANHO_TABULEIRO

    if not dentro_horizontal or not dentro_vertical:
        return None

    coluna = (x - X_TABULEIRO) // TAMANHO_CELULA
    linha = (y - Y_TABULEIRO) // TAMANHO_CELULA

    return int(linha), int(coluna)


def destacar_celula(frame, linha, coluna):
    """
    Destaca a célula apontada pelo dedo indicador.
    """
    x1 = X_TABULEIRO + coluna * TAMANHO_CELULA
    y1 = Y_TABULEIRO + linha * TAMANHO_CELULA
    x2 = x1 + TAMANHO_CELULA
    y2 = y1 + TAMANHO_CELULA
    overlay = frame.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 255, 255), -1)
    return cv2.addWeighted(overlay, 0.20, frame, 0.80, 0)


def reiniciar_jogo():
    """
    Cria um novo tabuleiro vazio.
    """
    return [
        ["", "", ""],
        ["", "", ""],
        ["", "", ""]
    ]


## Configurando o mediapipe para detecção da mão

mp_maos = mp.solutions.hands
mp_desenho = mp.solutions.drawing_utils
detector_maos = mp_maos.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.7)

## Condição inciial de jogo 

tabuleiro = reiniciar_jogo()
jogador_atual = "X"
resultado_jogo = None
instante_ultima_jogada = 0
pinca_ativa_anteriormente = False

## Configurando a câmera

camera = cv2.VideoCapture(0)
camera.set(cv2.CAP_PROP_FRAME_WIDTH, LARGURA_CAMERA)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, ALTURA_CAMERA)

## Main Loop do jogo

while True:
    sucesso, frame = camera.read()

    if not sucesso:
        print("Não foi possível acessar a câmera.")
        break

    frame = cv2.flip(frame, 1)
    altura_frame, largura_frame = frame.shape[:2] # Espelhando a imagem
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) # Convertendo BGR para RGB
    resultado_maos = detector_maos.process(frame_rgb) # Detectando a mão
    frame = desenhar_tabuleiro(frame, tabuleiro) # Desenhando o tabuleiro

    if resultado_maos.multi_hand_landmarks:
        for pontos_mao in resultado_maos.multi_hand_landmarks:
            mp_desenho.draw_landmarks(frame, pontos_mao, mp_maos.HAND_CONNECTIONS) # Desenhando os pontos da mão
            indicador = pontos_mao.landmark[8] # Landmark 8: ponta do indicador -- igual ao que foi feito na lousa magica hihihihiiih
            polegar = pontos_mao.landmark[4] # Landmark 4: ponta do polegar
            indicador_x = int(indicador.x * largura_frame)
            indicador_y = int(indicador.y * altura_frame)
            polegar_x = int(polegar.x * largura_frame)
            polegar_y = int(polegar.y * altura_frame)

            cv2.circle(frame, (indicador_x, indicador_y), 12, (0, 255, 255), -1) # cria o cursor virtual
            distancia = math.hypot(indicador_x - polegar_x, indicador_y - polegar_y) # calcula a distância entre o indicador e o polegar
            pinca_ativa = distancia < DISTANCIA_PINCA # verificando se a pinça está ativa (indicador e polegar próximos)
            celula = descobrir_celula(indicador_x, indicador_y) # Descobrindo a célula apontada

            if celula is not None:
                linha, coluna = celula
                frame = destacar_celula(frame, linha, coluna) # Destacando a célula atual

                tempo_atual = time.time()
                nova_pinca = pinca_ativa and not pinca_ativa_anteriormente
                tempo_liberado = tempo_atual - instante_ultima_jogada > TEMPO_ENTRE_JOGADAS
                casa_vazia = tabuleiro[linha][coluna] == ""
                jogo_em_andamento = resultado_jogo is None

                if nova_pinca and tempo_liberado and casa_vazia and jogo_em_andamento:
                    tabuleiro[linha][coluna] = jogador_atual
                    resultado_jogo = verificar_vencedor(tabuleiro)
                    if resultado_jogo is None:
                        if jogador_atual == "X":
                            jogador_atual = "O"
                        else:
                            jogador_atual = "X"
                    instante_ultima_jogada = tempo_atual
            pinca_ativa_anteriormente = pinca_ativa
            # Linha entre indicador e polegar
            if pinca_ativa:
                cor_pinca = (0, 255, 0)
            else:
                cor_pinca = (0, 150, 255)
            cv2.line(frame, (indicador_x, indicador_y), (polegar_x, polegar_y), cor_pinca, 3)

    else:
        pinca_ativa_anteriormente = False

    ## Mensagem de status do jogo

    if resultado_jogo == "X":
        mensagem = "X venceu!"

    elif resultado_jogo == "O":
        mensagem = "O venceu!"

    elif resultado_jogo == "EMPATE":
        mensagem = "Empate!"

    else:
        mensagem = f"Jogador atual: {jogador_atual}"
    
    cv2.putText(frame, mensagem, (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
    cv2.putText(frame, "Aponte e junte indicador + polegar", (30, altura_frame - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(frame, "R: reiniciar | ESC: sair", (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

    # Exibindo a câmera
    cv2.imshow("Jogo da Velha com as Maos", frame)
    tecla = cv2.waitKey(1) & 0xFF

    # ESC encerra o programa
    if tecla == 27:
        break

    # R reinicia o jogo
    if tecla == ord("r"):
        tabuleiro = reiniciar_jogo()
        jogador_atual = "X"
        resultado_jogo = None
        instante_ultima_jogada = 0
        pinca_ativa_anteriormente = False

camera.release()
detector_maos.close()
cv2.destroyAllWindows()
