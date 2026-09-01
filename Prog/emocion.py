import cv2
import numpy as np
import time
import math
import random
import threading
from fer.fer import FER

# ==========================================
# detecção de resolução
# ==========================================
def obter_resolucao_tela():
    """tenta descobrir a resolução real do monitor para desenhar os olhos no tamanho exato"""
    try:
        import tkinter as tk
        root = tk.Tk()
        # oculta a janela do tkinter
        root.attributes('-alpha', 0.0)
        w = root.winfo_screenwidth()
        h = root.winfo_screenheight()
        root.destroy()
        return w, h
    except:
        # se o tkinter não estiver disponível, usa uma resolução padrão
        return 1920, 1080

# pega o tamanho exato do seu monitor (ex: 1366x768, 1920x1080, etc)
TELA_W, TELA_H = obter_resolucao_tela()

# ==========================================
# configuração da Câmera
# ==========================================
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# inicialização de tela cheia corrigida
cv2.namedWindow("olhos", cv2.WINDOW_NORMAL)
cv2.setWindowProperty("olhos", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

# dá um primeiro push com a imagem no tamanho exato da tela
frame_inicial = np.zeros((TELA_H, TELA_W, 3), dtype=np.uint8)
cv2.imshow("olhos", frame_inicial)
cv2.waitKey(200) # pausa rápida pro linux entender e maximizar a tela

# ==========================================
# thread da IA
# ==========================================
detector = FER(mtcnn=False)
emocao_atual = 'neutral'
frame_para_analise = None
rodando = True

def ia_worker():
    global emocao_atual, frame_para_analise, rodando
    while rodando:
        if frame_para_analise is not None:
            frame = frame_para_analise.copy()
            small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
            result = detector.detect_emotions(small_frame)

            if result:
                maior_rosto = max(result, key=lambda f: f["box"][2] * f["box"][3])
                emotions = maior_rosto["emotions"]
                alvos = ['angry', 'sad', 'happy']
                filtradas = {k: emotions[k] for k in alvos if k in emotions}

                if filtradas:
                    dominante = max(filtradas, key=filtradas.get)
                    if filtradas[dominante] > 0.35:
                        emocao_atual = dominante
                    else:
                        emocao_atual = 'neutral'
            else:
                emocao_atual = 'neutral'
        
        time.sleep(0.15)

thread_ia = threading.Thread(target=ia_worker, daemon=True)
thread_ia.start()


# ==========================================
# classe de animação
# ==========================================
class animadorOlhos:
    def __init__(self):
        self.cor_olho = np.array([137.0, 31.0, 222.0])
        self.cor_glare = np.array([160.0, 55.0, 250.0])
        self.ang_esq = 0.0
        self.ang_dir = 0.0
        self.piscar_t = 0.0
        self.piscando = False
        self.ultimo_piscar = time.time()
        self.olhar_x = 0.0
        self.olhar_y = 0.0
        self.alvo_olhar_x = 0.0
        self.alvo_olhar_y = 0.0

    def lerp(self, atual, alvo, velocidade):
        return atual + (alvo - atual) * velocidade

    def atualizar_estado(self, emocao):
        if emocao == 'angry':
            alvo_olho = np.array([20, 20, 220])
            alvo_glare = np.array([80, 80, 255])
            alvo_ang_esq, alvo_ang_dir = -20, 20
        elif emocao == 'sad':
            alvo_olho = np.array([230, 100, 30])
            alvo_glare = np.array([255, 180, 100])
            alvo_ang_esq, alvo_ang_dir = 15, -15
        else: 
            alvo_olho = np.array([137, 31, 222])
            alvo_glare = np.array([160, 55, 250])
            alvo_ang_esq, alvo_ang_dir = 0, 0

        self.cor_olho = self.lerp(self.cor_olho, alvo_olho, 0.1)
        self.cor_glare = self.lerp(self.cor_glare, alvo_glare, 0.1)
        self.ang_esq = self.lerp(self.ang_esq, alvo_ang_esq, 0.15)
        self.ang_dir = self.lerp(self.ang_dir, alvo_ang_dir, 0.15)

        agora = time.time()
        if not self.piscando and agora - self.ultimo_piscar > random.uniform(2.0, 6.0):
            self.piscando = True
            self.piscar_t = 0.0

        escala_piscar = 1.0
        if self.piscando:
            self.piscar_t += 0.35 
            if self.piscar_t >= math.pi:
                self.piscando = False
                self.ultimo_piscar = agora
                self.piscar_t = 0.0
            else:
                escala_piscar = max(0.05, 1.0 - math.sin(self.piscar_t))

        if random.random() < 0.03: 
            self.alvo_olhar_x = random.uniform(-25, 25)
            self.alvo_olhar_y = random.uniform(-15, 15)
        
        self.olhar_x = self.lerp(self.olhar_x, self.alvo_olhar_x, 0.1)
        self.olhar_y = self.lerp(self.olhar_y, self.alvo_olhar_y, 0.1)

        return escala_piscar

    def desenhar(self, frame, cx, cy, raio, raio_glare, emocao, is_left, escala_piscar):
        c_olho = (int(self.cor_olho[0]), int(self.cor_olho[1]), int(self.cor_olho[2]))
        c_glare = (int(self.cor_glare[0]), int(self.cor_glare[1]), int(self.cor_glare[2]))
        angulo = self.ang_esq if is_left else self.ang_dir

        respiracao = math.sin(time.time() * 2) * 0.03
        escala_y = escala_piscar + respiracao
        escala_x = 1.0 - respiracao 

        cx_olho = int(cx + self.olhar_x)
        cy_olho = int(cy + self.olhar_y)
        cx_glare = int(cx + self.olhar_x * 0.4) 
        cy_glare = int(cy + self.olhar_y * 0.4)

        if emocao == 'happy' and escala_piscar > 0.2:
            espessura = int(raio * 0.08)
            topo = cy_olho - int(raio * 0.15 * escala_y)
            base_y = cy_olho + int(raio * 0.1 * escala_y)
            esquerda = cx_olho - int(raio * 0.4 * escala_x)
            direita = cx_olho + int(raio * 0.4 * escala_x)
            meio = cx_olho
            
            overlay = frame.copy()
            cv2.line(overlay, (esquerda, base_y), (meio, topo), c_glare, espessura * 3)
            cv2.line(overlay, (meio, topo), (direita, base_y), c_glare, espessura * 3)
            cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, frame)
            
            cv2.line(frame, (esquerda, base_y), (meio, topo), c_olho, espessura)
            cv2.line(frame, (meio, topo), (direita, base_y), c_olho, espessura)
            return

        glare_rx = int(raio_glare * 0.35 * escala_x)
        glare_ry = int(raio_glare * 0.70 * escala_y)
        
        overlay = frame.copy()
        cv2.ellipse(overlay, (cx_glare, cy_glare), (glare_rx, glare_ry), angulo, 0, 360, c_glare, -1)
        cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, frame)

        iris_rx = int(raio * 0.35 * escala_x)
        iris_ry = int(raio * 0.70 * escala_y)
        cv2.ellipse(frame, (cx_olho, cy_olho), (iris_rx, iris_ry), angulo, 0, 360, c_olho, -1)

animador = animadorOlhos()

while True:
    ret, cam = cap.read()
    if not ret:
        break

    frame_para_analise = cam.copy()

    # o frame agora tem EXATAMENTE a resolução do monitor (TELA_H x TELA_W)
    fundo = np.zeros((TELA_H, TELA_W, 3), dtype=np.uint8)

    # o tamanho e a posição dos olhos escalam automaticamente com a tela
    raio = int(min(TELA_W, TELA_H) * 0.40)
    raio_glare = int(min(TELA_W, TELA_H) * 0.45)
    esq_cx = TELA_W // 2 - int(TELA_W * 0.15)
    dir_cx = TELA_W // 2 + int(TELA_W * 0.15)
    cy = TELA_H // 2

    escala_piscar = animador.atualizar_estado(emocao_atual)

    animador.desenhar(fundo, esq_cx, cy, raio, raio_glare, emocao_atual, is_left=True, escala_piscar=escala_piscar)
    animador.desenhar(fundo, dir_cx, cy, raio, raio_glare, emocao_atual, is_left=False, escala_piscar=escala_piscar)

    cv2.imshow("olhos", fundo)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        rodando = False 
        break

cap.release()
thread_ia.join()
cv2.destroyAllWindows()