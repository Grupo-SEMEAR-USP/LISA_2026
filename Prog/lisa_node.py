import os
import time
import threading
import subprocess
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import speech_recognition as sr
import pygame
import ollama
#aq eu tô dando a voz da lisa e o modelo ia dela respectivamente
VOICE_MODEL = "pt-BR-ThalitaNeural"
OLLAMA_MODEL = "llama3.2"
#cria o publisher e manda um logger pra mim pra confirmar início, faz o cognitive loop restart pra n responder 1 vez só (acho q é isso)
class LisaBrainNode(Node):
    def __init__(self):
        super().__init__('lisa_brain_node')
        self.publisher_hardware = self.create_publisher(String, '/lisa/comandos', 10)
        self.get_logger().info('L.I.S.A. ROS 2 Node Iniciado.')
        threading.Thread(target=self.cognitive_loop, daemon=True).start()
#tirei algumas pausas pq tava atrasando dms as falas da lisa, demorava uns 10 segundos pra retomar a fala depois do ponto
    def speak(self, text):
        pygame.mixer.init()
        text_for_tts = text.replace('.', ',').replace('!', ',').replace('?', ',')
        filename = "temp_lisa_voice.mp3"
        subprocess.run(["edge-tts", "--voice", VOICE_MODEL, "--text", text_for_tts, "--write-media", filename], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(filename):
            pygame.mixer.music.load(filename)
            self.publisher_hardware.publish(String(data="acao:falar"))
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy(): time.sleep(0.05)
            pygame.mixer.music.unload()
            os.remove(filename)
            self.publisher_hardware.publish(String(data="acao:silencio"))

    def cognitive_loop(self):
        rec = sr.Recognizer()
        
        # 1. tolerância de silêncio aumentada para você pensar sem ser cortado
        rec.pause_threshold = 1.2  
        
        # 2. desativa o ganho automático para o barulho de fundo não bugar todo script
        rec.dynamic_energy_threshold = False
        
        # 3. linha de corte alta: origa a falar perto do microfone e ignora o resto (tem q falar perto do mic basicamente, ela filtra os db do input de áudio)
        rec.energy_threshold = 1200 

#prompt pra lisa inicializar com a personalidade dela, legal vcs lerem e comentar mudanças
        system_prompt = "Você é a L.I.S.A., uma IA brilhante em um robô ROS 2. REGRAS: Responda SEMPRE com no máximo 1 a 2 frases curtas. Seja simples, direta e encante crianças e investidores. Zero formatações."
        history = [{'role': 'system', 'content': system_prompt}]

        self.speak("Sistemas iniciados.")

#só pra ver se funfa
        with sr.Microphone() as mic:
            self.get_logger().info("=========================================")
            self.get_logger().info("MODO COMPETITIVO ATIVADO. FALE PERTO DO MICROFONE!")
            self.get_logger().info("=========================================")
#aqui ela dá um feedback visual inicialmente pra testes, na lisa n vai ter isso, ou vamos ter q integrar tipo uma tela de ouvindo ou algo assim pra cada coisa pra ter algum feedback visual, mas vai provavelmente levar ainda mais tempo pra resolver por causa do uso de ram             
            while rclpy.ok():
                self.get_logger().info("Ouvindo...")
                #tenta ouvir o mic por no max 8seg, se n ouvir nada ou der algum erro dá timeout erro, basicamente tratamento de erro necessário básico pra tudo
                try:
                    audio = rec.listen(mic, timeout=5, phrase_time_limit=8)
                except sr.WaitTimeoutError:
                    continue
                #feedback visual dnv
                try:
                    self.get_logger().info("Decodificando fala...")
                    user_text = rec.recognize_google(audio, language="pt-BR")
                    if not user_text.strip(): continue
                    #feedback visual
                    self.get_logger().info(f"VOCÊ: {user_text}")
                    history.append({'role': 'user', 'content': user_text})
                    
                    response = ollama.chat(model=OLLAMA_MODEL, messages=history, stream=False)
                    resposta_texto = response['message']['content']
                    #feedback visual resposta da lisa
                    self.get_logger().info(f"L.I.S.A.: {resposta_texto}")
                    history.append({'role': 'assistant', 'content': resposta_texto})
                    self.speak(resposta_texto)
                    #isso aq é tratamento de erro pra bo federal
                except sr.UnknownValueError:
                    pass 
                except Exception as e:
                    self.get_logger().error(f"Erro: {e}")
#instalando o "cérebro" dela via internete com o rclpy pra ros
def main(args=None):
    rclpy.init(args=args)
    lisa_node = LisaBrainNode()
    try:
        rclpy.spin(lisa_node)
    except KeyboardInterrupt:
        pass
        #shutdown lisa pra n dar bo depois de fazer algo como dar um ctrl c no terminal, basicamente um dois em 1 pra n dar bo e ter como desligar
    finally:
        lisa_node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
