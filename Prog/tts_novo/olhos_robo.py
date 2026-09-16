import cv2
import numpy as np
import time
import random
import re
import subprocess

# ---------- RESOLUÇÃO AUTOMÁTICA DA TELA ----------
def obter_resolucao_tela():
    # 1) xrandr (X11/XWayland) - não depende de tkinter, evita o conflito
    #    de lib do snap (libpthread/core20) que trava com Tk em algumas máquinas
    try:
        saida = subprocess.check_output(
            ['xrandr'], stderr=subprocess.DEVNULL, timeout=2
        ).decode()
        linhas_conectadas = [l for l in saida.splitlines() if ' connected' in l]
        # prioriza o monitor marcado como primary
        for linha in linhas_conectadas:
            if 'primary' in linha:
                m = re.search(r'(\d+)x(\d+)\+\d+\+\d+', linha)
                if m:
                    return int(m.group(1)), int(m.group(2))
        # senão pega o primeiro conectado
        for linha in linhas_conectadas:
            m = re.search(r'(\d+)x(\d+)\+\d+\+\d+', linha)
            if m:
                return int(m.group(1)), int(m.group(2))
    except Exception:
        pass

    # 2) tkinter como segunda opção (pode falhar em sistemas com LD_LIBRARY_PATH
    #    contaminado por algum snap - se falhar, cai no fallback abaixo)
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        largura = root.winfo_screenwidth()
        altura = root.winfo_screenheight()
        root.destroy()
        if largura > 0 and altura > 0:
            return largura, altura
    except Exception:
        pass

    return 1280, 720  # fallback final

LARG_TELA, ALT_TELA = obter_resolucao_tela()

# Escala tudo com base no design original (feito pra 800x600)
ESCALA = ALT_TELA / 600.0

CAM_RES_LARG = 640
CAM_RES_ALT = 480
W_NOME = 'Simulacao Olhos Rosa'

OLHO_RAIO_X = int(50 * ESCALA)
OLHO_RAIO_Y = int(80 * ESCALA)
OLHO_COR = (255, 100, 255)  # Rosa exato
OLHO_SEP_X = int(180 * ESCALA)
OLHO_CENTRO_Y = ALT_TELA // 2
AMPLITUDE_X = int(60 * ESCALA)
AMPLITUDE_Y = int(40 * ESCALA)

# CONFIGURAÇÕES SIMULADAS DO MOTOR (0 a 180 graus)
SERVO_PAN_LIMITS = [0, 180]
SERVO_TILT_LIMITS = [0, 180]
SERVO_PAN_CENTER = 90
SERVO_TILT_CENTER = 90
SERVO_SMOOTH_FACTOR = 0.3

# LÓGICA DE TEMPO
TEMPO_PERDIDO_LIMIAR = 2.0
BUSCA_AMP_PAN = 30
BUSCA_AMP_TILT = 15

# Inicializa Câmera
face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_RES_LARG)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_RES_ALT)

# Janela em Tela Cheia
cv2.namedWindow(W_NOME, cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty(W_NOME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

pan_current = SERVO_PAN_CENTER
tilt_current = SERVO_TILT_CENTER
time_lost = time.time()
is_lost = False
last_valid_face_pos = (CAM_RES_LARG // 2, CAM_RES_ALT // 2)


def smooth_move(current, target, factor, limits):
    new_val = current + (target - current) * factor
    return max(limits[0], min(limits[1], new_val))


def desenhar_olho(frame, centro, raio_x, raio_y, cor_base):
    """Olho com glow suave + núcleo sólido + brilho glossy, tudo com anti-aliasing."""
    cx, cy = centro
    pad = int(max(raio_x, raio_y) * 0.8)
    glow_w = (raio_x + pad) * 2
    glow_h = (raio_y + pad) * 2

    # camada de brilho (glow), desenhada e borrada isoladamente (mais barato que borrar o frame todo)
    local = np.zeros((glow_h, glow_w, 3), np.uint8)
    cv2.ellipse(local, (glow_w // 2, glow_h // 2), (int(raio_x * 1.3), int(raio_y * 1.3)),
                0, 0, 360, cor_base, -1, cv2.LINE_AA)
    local = cv2.GaussianBlur(local, (0, 0), sigmaX=max(raio_x * 0.4, 1))

    x0, y0 = cx - glow_w // 2, cy - glow_h // 2
    x1, y1 = x0 + glow_w, y0 + glow_h
    fx0, fy0 = max(x0, 0), max(y0, 0)
    fx1, fy1 = min(x1, frame.shape[1]), min(y1, frame.shape[0])
    lx0, ly0 = fx0 - x0, fy0 - y0
    lx1, ly1 = lx0 + (fx1 - fx0), ly0 + (fy1 - fy0)

    if fx1 > fx0 and fy1 > fy0:
        roi = frame[fy0:fy1, fx0:fx1]
        glow_crop = local[ly0:ly1, lx0:lx1]
        frame[fy0:fy1, fx0:fx1] = cv2.max(roi, glow_crop)

    # núcleo sólido
    cv2.ellipse(frame, (cx, cy), (raio_x, raio_y), 0, 0, 360, cor_base, -1, cv2.LINE_AA)

    # reflexo glossy (dá a sensação de "tela"/plástico)
    hl_color = tuple(min(255, c + 70) for c in cor_base)
    cv2.ellipse(frame, (cx - raio_x // 3, cy - int(raio_y * 0.55)),
                (max(raio_x // 4, 4), max(raio_y // 5, 4)), 0, 0, 360, hl_color, -1, cv2.LINE_AA)


def desenhar_interface(pan_val, tilt_val, arrow_type):
    clean_frame = np.zeros((ALT_TELA, LARG_TELA, 3), np.uint8)

    visual_offset_x = np.interp(pan_val, [0, 180], [-AMPLITUDE_X, AMPLITUDE_X])
    visual_offset_y = np.interp(tilt_val, [0, 180], [-AMPLITUDE_Y, AMPLITUDE_Y])

    olho_esq_x = int(LARG_TELA // 2 - OLHO_SEP_X // 2 + visual_offset_x)
    olho_esq_y = int(OLHO_CENTRO_Y + visual_offset_y)
    olho_dir_x = int(LARG_TELA // 2 + OLHO_SEP_X // 2 + visual_offset_x)
    olho_dir_y = int(OLHO_CENTRO_Y + visual_offset_y)

    desenhar_olho(clean_frame, (olho_esq_x, olho_esq_y), OLHO_RAIO_X, OLHO_RAIO_Y, OLHO_COR)
    desenhar_olho(clean_frame, (olho_dir_x, olho_dir_y), OLHO_RAIO_X, OLHO_RAIO_Y, OLHO_COR)

    if arrow_type:
        arrow_thickness = max(int(10 * ESCALA), 2)
        arrow_len = int(150 * ESCALA)
        arrow_head_len = int(50 * ESCALA)
        arrow_color = (150, 0, 150)
        off1 = int(250 * ESCALA)
        p1 = p2 = None

        if arrow_type == 'esq':
            p1 = (LARG_TELA // 2 - off1, ALT_TELA // 2)
            p2 = (p1[0] - arrow_len, ALT_TELA // 2)
        elif arrow_type == 'dir':
            p1 = (LARG_TELA // 2 + off1, ALT_TELA // 2)
            p2 = (p1[0] + arrow_len, ALT_TELA // 2)
        elif arrow_type == 'cima':
            p1 = (LARG_TELA // 2, ALT_TELA // 2 - off1)
            p2 = (LARG_TELA // 2, p1[1] - arrow_len)
        elif arrow_type == 'baixo':
            p1 = (LARG_TELA // 2, ALT_TELA // 2 + off1)
            p2 = (LARG_TELA // 2, p1[1] + arrow_len)

        if p1 and p2:
            cv2.arrowedLine(clean_frame, p1, p2, arrow_color, arrow_thickness,
                             line_type=cv2.LINE_AA, tipLength=arrow_head_len / arrow_len)

    return clean_frame


while True:
    ret, cam_frame = cap.read()
    if not ret:
        break

    cam_frame = cv2.flip(cam_frame, 1)
    gray = cv2.cvtColor(cam_frame, cv2.COLOR_BGR2GRAY)
    rostos = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5, minSize=(30, 30))

    arrow_dir = None

    if len(rostos) > 0:
        is_lost = False
        time_lost = time.time()

        rostos = sorted(rostos, key=lambda x: x[2] * x[3], reverse=True)
        (x, y, w, h) = rostos[0]

        centro_x = x + (w // 2)
        centro_y = y + (h // 2)
        last_valid_face_pos = (centro_x, centro_y)

        # frame já espelhado (flip) -> x cresce pra direita do usuário, mapeamento direto
        pan_target = np.interp(centro_x, [0, CAM_RES_LARG], [0, 180])
        tilt_target = np.interp(centro_y, [0, CAM_RES_ALT], [0, 180])

    else:
        tempo_sem_rosto = time.time() - time_lost

        if tempo_sem_rosto < TEMPO_PERDIDO_LIMIAR:
            last_x, last_y = last_valid_face_pos
            margin = 50
            if last_x < margin:
                arrow_dir = 'esq'
            elif last_x > CAM_RES_LARG - margin:
                arrow_dir = 'dir'
            elif last_y < margin:
                arrow_dir = 'cima'
            elif last_y > CAM_RES_ALT - margin:
                arrow_dir = 'baixo'

            pan_target = pan_current
            tilt_target = tilt_current

        else:
            if not is_lost:
                is_lost = True

            pan_target = SERVO_PAN_CENTER + random.randint(-BUSCA_AMP_PAN, BUSCA_AMP_PAN)
            tilt_target = SERVO_TILT_CENTER + random.randint(-BUSCA_AMP_TILT, BUSCA_AMP_TILT)

    pan_current = smooth_move(pan_current, pan_target, SERVO_SMOOTH_FACTOR, SERVO_PAN_LIMITS)
    tilt_current = smooth_move(tilt_current, tilt_target, SERVO_SMOOTH_FACTOR, SERVO_TILT_LIMITS)

    output_frame = desenhar_interface(pan_current, tilt_current, arrow_dir)

    cv2.imshow(W_NOME, output_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
