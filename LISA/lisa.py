import cv2
import numpy as np

face_det  = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
smile_det = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_smile.xml")
eye_det   = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")

COR = (161, 141, 255)

ox, oy    = 0.0, 0.0
ax, ay    = 0.0, 0.0
tick      = 0
mimetismo = False
emo_scores = {"neutral":1.0,"happy":0.0,"sad":0.0,"angry":0.0,"surprised":0.0}

W, H = 1280, 720


def blob(img, cx, cy, rx, ry):
    for i in range(6, 0, -1):
        g = tuple(int(c * 0.11 * i) for c in COR)
        cv2.ellipse(img, (cx,cy), (rx+i*8, ry+i*8), 0, 0, 360, g, -1)
    cv2.ellipse(img, (cx,cy), (rx,ry), 0, 0, 360, COR, -1)
    cv2.ellipse(img,
                (cx - int(rx*0.26), cy - int(ry*0.26)),
                (int(rx*0.18), int(ry*0.14)),
                0, 0, 360, (255,255,255), -1)


def linha_glow(img, p1, p2, esp):
    for i in range(6, 0, -1):
        g = tuple(int(c * 0.09 * i) for c in COR)
        cv2.line(img, p1, p2, g, esp+i*6, cv2.LINE_AA)
    cv2.line(img, p1, p2, COR, esp, cv2.LINE_AA)


def olho_feliz(img, cx, cy, r):
    esp = max(4, int(r * 0.32))
    linha_glow(img, (cx - int(r*0.82), cy + int(r*0.20)), (cx, cy - int(r*0.32)), esp)
    linha_glow(img, (cx, cy - int(r*0.32)), (cx + int(r*0.82), cy + int(r*0.20)), esp)


def olho_bravo_esq(img, cx, cy, r):
    esp = max(4, int(r * 0.32))
    linha_glow(img,
               (cx - int(r*0.70), cy - int(r*0.28)),
               (cx + int(r*0.70), cy + int(r*0.28)), esp)


def olho_bravo_dir(img, cx, cy, r):
    esp = max(4, int(r * 0.32))
    linha_glow(img,
               (cx - int(r*0.70), cy + int(r*0.28)),
               (cx + int(r*0.70), cy - int(r*0.28)), esp)


def desenhar_olhos(img, lx, rx, cy2, r, dx, dy, em):
    if em == "happy":
        olho_feliz(img, lx, cy2, r)
        olho_feliz(img, rx, cy2, r)
    elif em == "angry":
        olho_bravo_esq(img, lx, cy2, r)
        olho_bravo_dir(img, rx, cy2, r)
    elif em == "surprised":
        blob(img, lx, cy2, int(r*0.72), int(r*1.10))
        blob(img, rx, cy2, int(r*0.72), int(r*1.10))
    elif em == "sad":
        blob(img, lx, cy2 + int(r*0.12), int(r*0.52), int(r*0.72))
        blob(img, rx, cy2 + int(r*0.12), int(r*0.52), int(r*0.72))
    else:
        px = int(dx * r * 0.42)
        py = int(dy * r * 0.32)
        blob(img, lx + px, cy2 + py, int(r*0.52), int(r*0.78))
        blob(img, rx + px, cy2 + py, int(r*0.52), int(r*0.78))


def detectar(gray, face):
    x, y, w, h = face
    roi = gray[y:y+h, x:x+w]
    s = {"neutral":0.4,"happy":0.0,"sad":0.0,"angry":0.0,"surprised":0.0}

    smiles = smile_det.detectMultiScale(
        roi, scaleFactor=1.5, minNeighbors=10,
        minSize=(int(w*0.20), int(h*0.06)))
    if len(smiles):
        s["happy"] += 0.8
        s["angry"] -= 0.3

    eyes     = eye_det.detectMultiScale(roi, 1.1, 4, minSize=(int(w*0.08), int(h*0.06)))
    eye_area = sum(ew*eh for _,_,ew,eh in eyes) / (w*h) if len(eyes) else 0
    if len(eyes) >= 2:
        s["surprised"] += 0.6 if eye_area > 0.07 else 0.0
        s["neutral"]   += 0.0 if eye_area > 0.07 else 0.3
    elif len(eyes) == 1:
        s["angry"] += 0.2

    if w / max(h, 1) < 0.70:
        s["surprised"] += 0.4

    for k in s:
        if s[k] < 0:
            s[k] = 0.0
    t = sum(s.values()) or 1
    return {k: v/t for k, v in s.items()}


def main():
    global ox, oy, ax, ay, tick, mimetismo, emo_scores

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    cv2.namedWindow("LISA", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty("LISA", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    raio = int(min(W, H) * 0.36)
    gap  = int(W * 0.28)
    lx   = W//2 - gap
    rx   = W//2 + gap
    cy2  = H//2

    while True:
        ret, cam = cap.read()
        if not ret:
            break
        cam = cv2.flip(cam, 1)
        ch, cw = cam.shape[:2]

        fundo = np.zeros((H, W, 3), dtype=np.uint8)

        gray   = cv2.cvtColor(cam, cv2.COLOR_BGR2GRAY)
        rostos = face_det.detectMultiScale(gray, 1.1, 5, minSize=(60,60))

        tick    += 1
        blinking = (tick % 150) < 8

        if len(rostos) > 0:
            xf, yf, wf, hf = sorted(rostos, key=lambda r: r[2]*r[3], reverse=True)[0]
            ax = ((xf + wf//2) / cw - 0.5) * 2.0
            ay = ((yf + hf//2) / ch - 0.5) * 2.0
            if mimetismo:
                raw = detectar(gray, (xf, yf, wf, hf))
                for k in emo_scores:
                    emo_scores[k] += (raw.get(k, 0) - emo_scores[k]) * 0.15
        else:
            ax, ay = 0.0, 0.0

        ox += (ax - ox) * 0.12
        oy += (ay - oy) * 0.12

        dom = max(emo_scores, key=emo_scores.get)
        em  = "happy" if blinking else (dom if mimetismo else "neutral")

        desenhar_olhos(fundo, lx, rx, cy2, raio, ox, oy, em)

        if mimetismo and dom == "sad" and not blinking:
            for ex in [lx, rx]:
                ey = cy2 + int(raio * 0.88)
                for i in range(5, 0, -1):
                    g = tuple(int(c*0.10*i) for c in COR)
                    cv2.circle(fundo, (ex, ey), int(raio*.06)+i*3, g, -1)
                cv2.circle(fundo, (ex, ey), int(raio*.06), COR, -1)

        hint = "M = sair mimetismo" if mimetismo else "M = mimetismo"
        tw   = cv2.getTextSize(hint, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0][0]
        cv2.putText(fundo, hint, (W//2 - tw//2, H-18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (50,40,70), 1, cv2.LINE_AA)

        cv2.imshow("LISA", fundo)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        if key in (ord('m'), ord('M')):
            mimetismo = not mimetismo
            if not mimetismo:
                emo_scores = {"neutral":1.0,"happy":0.0,"sad":0.0,"angry":0.0,"surprised":0.0}

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
