import cv2
import numpy as np

#É O NREE

detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

ox = 0.0
oy = 0.0

def desenhar_olho(frame, cx, cy, raio, dx, dy, piscando):

    if piscando:
        espessura = 30
        cor = (161, 141, 255)
        topo = cy - int(raio * 0.3) 
        base_y = cy + int(raio * 0.2)
        esquerda = cx - int(raio * 0.8)
        direita  = cx + int(raio * 0.8)
        meio     = cx
        # linha esquerda do ^
        cv2.line(frame, (esquerda, base_y), (meio, topo), cor, espessura)
        # linha direita do ^
        cv2.line(frame, (meio, topo), (direita, base_y), cor, espessura)
    else:
        iris_rx = int(raio * 0.42)
        iris_ry = int(raio * 0.60)
        pdx = int(dx * raio * 0.7)
        pdy = int(dy * raio * 0.55)
        px = cx + pdx
        py = cy + pdy

        cv2.ellipse(frame, (px, py), (iris_rx, iris_ry), 0, 0, 360, (161, 141, 255), -1)

        rx = px - int(iris_rx * 0.25)
        ry = py - int(iris_ry * 0.25)
        cv2.circle(frame, (rx, ry), int(iris_rx * 0.2), (255, 255, 255), -1)

def main():
    global ox, oy

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    cv2.namedWindow("olhos", cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty("olhos", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    alvo_x, alvo_y = 0.0, 0.0
    tick = 0

    while True:
        ret, cam = cap.read()
        if not ret:
            break

        cam = cv2.flip(cam, 1)
        ch, cw = cam.shape[:2]

        cinza = cv2.cvtColor(cam, cv2.COLOR_BGR2GRAY)
        rostos = detector.detectMultiScale(cinza, 1.1, 5, minSize=(60, 60))

        if len(rostos) > 0:
            x, y, w, h = sorted(rostos, key=lambda r: r[2]*r[3], reverse=True)[0]
            fx = (x + w // 2) / cw
            fy = (y + h // 2) / ch
            alvo_x = (fx - 0.5) * 2.0
            alvo_y = (fy - 0.5) * 2.0

        ox += (alvo_x - ox) * 0.15
        oy += (alvo_y - oy) * 0.15

        tick += 1
        piscando = (tick % 150) < 10

        W = cv2.getWindowImageRect("olhos")[2]
        H = cv2.getWindowImageRect("olhos")[3]
        if W <= 0 or H <= 0:
            W, H = 1280, 720

        fundo = np.zeros((H, W, 3), dtype=np.uint8)

        raio = int(min(W, H) * 0.28)
        esq_cx = W // 2 - int(W * 0.23)
        dir_cx = W // 2 + int(W * 0.23)
        cy = H // 2

        desenhar_olho(fundo, esq_cx, cy, raio, ox, oy, piscando)
        desenhar_olho(fundo, dir_cx, cy, raio, ox, oy, piscando)

        cv2.imshow("olhos", fundo)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()