#!/usr/bin/env python3
"""
Subscreve : /camera/image_raw   (sensor_msgs/Image)
Publica   : /lisa/emotion        (std_msgs/String)
            /lisa/emotion_scores (std_msgs/String)  JSON com todos os scores

Teclas na janela:
  M  — alterna idle / mimetismo
  Q  — encerra o nó
"""

import cv2
import numpy as np
import json
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge

# ── detectores ──────────────────────────────────────────────
face_det  = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
smile_det = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_smile.xml")
eye_det   = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")

COR = (161, 141, 255)
W, H = 1280, 720


# ── helpers de desenho (igual ao standalone) ────────────────
def blob(img, cx, cy, rx, ry):
    for i in range(6, 0, -1):
        g = tuple(int(c * 0.11 * i) for c in COR)
        cv2.ellipse(img, (cx, cy), (rx+i*8, ry+i*8), 0, 0, 360, g, -1)
    cv2.ellipse(img, (cx, cy), (rx, ry), 0, 0, 360, COR, -1)
    cv2.ellipse(img,
                (cx - int(rx*0.26), cy - int(ry*0.26)),
                (int(rx*0.18), int(ry*0.14)),
                0, 0, 360, (255, 255, 255), -1)


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
    s = {"neutral": 0.4, "happy": 0.0, "sad": 0.0, "angry": 0.0, "surprised": 0.0}

    smiles = smile_det.detectMultiScale(
        roi, scaleFactor=1.5, minNeighbors=10,
        minSize=(int(w*0.20), int(h*0.06)))
    if len(smiles):
        s["happy"] += 0.8
        s["angry"] -= 0.3

    eyes     = eye_det.detectMultiScale(roi, 1.1, 4, minSize=(int(w*0.08), int(h*0.06)))
    eye_area = sum(ew*eh for _, _, ew, eh in eyes) / (w*h) if len(eyes) else 0
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


# ── Nó ROS 2 ────────────────────────────────────────────────
class LisaNode(Node):
    def __init__(self):
        super().__init__("lisa_node")

        self.bridge = CvBridge()

        # subscriber câmera
        self.sub = self.create_subscription(
            Image, "/camera/image_raw",
            self.callback_imagem, 10)

        # publishers
        self.pub_emotion = self.create_publisher(String, "/lisa/emotion", 10)
        self.pub_scores  = self.create_publisher(String, "/lisa/emotion_scores", 10)

        # timer para o loop de display (~30 fps)
        self.timer = self.create_timer(1.0 / 30.0, self.loop_display)

        # estado
        self.ultimo_frame = None
        self.ox = 0.0
        self.oy = 0.0
        self.ax = 0.0
        self.ay = 0.0
        self.tick      = 0
        self.mimetismo = False
        self.emo_scores = {"neutral":1.0,"happy":0.0,"sad":0.0,"angry":0.0,"surprised":0.0}
        self.dom        = "neutral"

        # janela
        cv2.namedWindow("LISA", cv2.WINDOW_NORMAL)
        cv2.setWindowProperty("LISA", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

        self.raio = int(min(W, H) * 0.36)
        self.gap  = int(W * 0.28)
        self.lx   = W//2 - self.gap
        self.rx   = W//2 + self.gap
        self.cy2  = H//2

        self.get_logger().info("LISA pronta. Subscrevendo /camera/image_raw")
        self.get_logger().info("Publicando /lisa/emotion e /lisa/emotion_scores")
        self.get_logger().info("Tecla M = alterna mimetismo | Q = sair")

    def callback_imagem(self, msg: Image):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
            self.ultimo_frame = cv2.flip(frame, 1)
        except Exception as e:
            self.get_logger().warn(f"Erro ao converter imagem: {e}")

    def loop_display(self):
        fundo = np.zeros((H, W, 3), dtype=np.uint8)

        self.tick += 1
        blinking = (self.tick % 150) < 8

        if self.ultimo_frame is not None:
            frame = self.ultimo_frame
            ch, cw = frame.shape[:2]
            gray   = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            rostos = face_det.detectMultiScale(gray, 1.1, 5, minSize=(60, 60))

            if len(rostos) > 0:
                xf, yf, wf, hf = sorted(rostos, key=lambda r: r[2]*r[3], reverse=True)[0]
                self.ax = ((xf + wf//2) / cw - 0.5) * 2.0
                self.ay = ((yf + hf//2) / ch - 0.5) * 2.0

                if self.mimetismo:
                    raw = detectar(gray, (xf, yf, wf, hf))
                    for k in self.emo_scores:
                        self.emo_scores[k] += (raw.get(k, 0) - self.emo_scores[k]) * 0.15

                    # publica emoção dominante
                    self.dom = max(self.emo_scores, key=self.emo_scores.get)
                    msg_em = String()
                    msg_em.data = self.dom
                    self.pub_emotion.publish(msg_em)

                    # publica todos os scores como JSON
                    msg_sc = String()
                    msg_sc.data = json.dumps(
                        {k: round(v, 3) for k, v in self.emo_scores.items()})
                    self.pub_scores.publish(msg_sc)
            else:
                self.ax, self.ay = 0.0, 0.0

        self.ox += (self.ax - self.ox) * 0.12
        self.oy += (self.ay - self.oy) * 0.12

        em = "happy" if blinking else (self.dom if self.mimetismo else "neutral")

        desenhar_olhos(fundo, self.lx, self.rx, self.cy2,
                       self.raio, self.ox, self.oy, em)

        # lágrima
        if self.mimetismo and self.dom == "sad" and not blinking:
            for ex in [self.lx, self.rx]:
                ey = self.cy2 + int(self.raio * 0.88)
                for i in range(5, 0, -1):
                    g = tuple(int(c*0.10*i) for c in COR)
                    cv2.circle(fundo, (ex, ey), int(self.raio*.06)+i*3, g, -1)
                cv2.circle(fundo, (ex, ey), int(self.raio*.06), COR, -1)

        hint = "M = sair mimetismo" if self.mimetismo else "M = mimetismo"
        tw   = cv2.getTextSize(hint, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0][0]
        cv2.putText(fundo, hint, (W//2 - tw//2, H-18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (50, 40, 70), 1, cv2.LINE_AA)

        cv2.imshow("LISA", fundo)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q') or key == ord('Q'):
            self.get_logger().info("Encerrando LISA...")
            rclpy.shutdown()

        if key == ord('m') or key == ord('M'):
            self.mimetismo = not self.mimetismo
            if not self.mimetismo:
                self.emo_scores = {"neutral":1.0,"happy":0.0,"sad":0.0,"angry":0.0,"surprised":0.0}
                self.dom = "neutral"
            self.get_logger().info(
                f"Mimetismo {'ATIVO' if self.mimetismo else 'INATIVO'}")


def main(args=None):
    rclpy.init(args=args)
    node = LisaNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
