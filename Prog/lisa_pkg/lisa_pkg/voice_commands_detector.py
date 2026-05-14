#!/usr/bin/env python3

from std_msgs.msg import String

import rclpy
from rclpy.node import Node

import os
import time
import subprocess
import wave
import numpy as np
from pathlib import Path
from faster_whisper import WhisperModel
from unidecode import unidecode
import threading

'''
Detector de comandos de voz.

    Tópico publicado: /voice_command
        - Tipo da mensagem: std_msgs/msg/String 

'''

class VoiceCommandsDetectorNode(Node):

    def __init__(self):
        super().__init__("voice_commands_detector")
        self.publisher_ =  self.create_publisher(String, "voice_command", 10)

        # Preferred capture settings 
        self.PREF_SAMPLE_RATE = 16000
        self.PREF_CHANNELS = 1
        # VAD settings
        self.FRAME_MS = 30
        self.SILENCE_THRESHOLD = 120   # Base RMS
        self.END_SILENCE_MS = 800
        self.MIN_SPEECH_MS = 300
        self.MAX_RECORDING_MS = 15000
        # Models
        self.WHISPER_MODEL = "small"
        # Conversation
        self.AUTO_RESTART_DELAY = 1.5
        # Temp file
        self.TEMP_WAV = Path("/tmp/recording.wav")
        # Optional: force a specific PipeWire source (id or name)
        self.MIC_TARGET = os.environ.get("MIC_TARGET")

        self.whisper_ = WhisperModel(
            self.WHISPER_MODEL,
            device="cpu",
            compute_type="int8",
            cpu_threads=4,
            download_root=str(Path.home() / ".cache" / "whisper")
        )

        self.stt_thread_ = threading.Thread(target=self.stt_loop, daemon=True)
        self.stt_thread_.start()

        self.wake_words_ = ["ei lisa", "oi lisa", "e ai lisa", "hei lisa", "hey lisa"]
        self.voice_commands_ = ["ativar modo mimica", "ativar modo gestos"]

        self.get_logger().info(f"Nó '{self.get_name()}' inicializado com sucesso.")


    def _spawn_pw_cat_record(self, rate, channels, target):
        cmd = [
            "pw-cat", "--record", "-",
            "--format", "s16",
            "--rate", str(rate),
            "--channels", str(channels)
        ]
        if target:
            cmd += ["--target", str(target)]
        return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


    def _select_record_pipeline(self, target):
        """
        Try a few (rate,channels) combos so we don't crash if the device
        refuses 16k mono. Returns (proc, rate, channels, first_chunk or None, err_text).
        """
        attempts = [
            (self.PREF_SAMPLE_RATE, self.PREF_CHANNELS),  # 16k / mono
            (self.PREF_SAMPLE_RATE, 2),              # 16k / stereo
            (48000, self.PREF_CHANNELS),             # 48k / mono
            (48000, 2),                         # 48k / stereo
        ]
        for rate, ch in attempts:
            proc = self._spawn_pw_cat_record(rate, ch, target)
            bytes_per_sample = 2
            frame_bytes = int(rate * self.FRAME_MS / 1000) * bytes_per_sample * ch
            chunk = proc.stdout.read(frame_bytes)
            if chunk:
                return proc, rate, ch, chunk, ""
            err = (proc.stderr.read() or b"").decode("utf-8", errors="ignore")
            try:
                proc.terminate(); proc.wait(timeout=0.5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
            if err.strip():
                self.get_logger().error(f"Erro: pw-cat refused {rate}Hz/{ch}ch: {err.strip()}")
            else:
                self.get_logger().error(f"Erro: pw-cat produced no data at {rate}Hz/{ch}ch, retrying...")
        return None, None, None, None, "No working pw-cat configuration found"


    def record_with_vad(self, timeout_seconds=30):
        """Record audio until silence is detected (VAD). Returns (bytes, rate, channels) or (None, None, None)."""
        self.get_logger().info("Ouvindo... (fale agora)")
        if self.MIC_TARGET:
            self.get_logger().info(f"Using source target: {self.MIC_TARGET}")

        proc, rate, ch, first_chunk, err = self._select_record_pipeline(self.MIC_TARGET)
        if not proc:
            self.get_logger().error(f"Erro: {err}")
            return None, None, None

        bytes_per_sample = 2
        frame_bytes = int(rate * self.FRAME_MS / 1000) * bytes_per_sample * ch
        audio_buffer = bytearray()

        try:
            # Quick calibration (~300ms)
            noise_samples = []
            if first_chunk:
                s = np.frombuffer(first_chunk, dtype=np.int16).astype(np.float32)
                noise_samples.append(float(np.sqrt(np.mean(s * s))))
            for _ in range(9):
                chunk = proc.stdout.read(frame_bytes)
                if chunk:
                    s = np.frombuffer(chunk, dtype=np.int16).astype(np.float32)
                    noise_samples.append(float(np.sqrt(np.mean(s * s))))
            noise_floor = float(np.median(noise_samples)) if noise_samples else 50.0
            threshold = max(self.SILENCE_THRESHOLD, noise_floor * 1.8)

            is_speaking = False
            silence_ms = 0
            speech_ms = 0
            total_ms = 0
            start = time.time()

            if first_chunk is not None:
                samples = np.frombuffer(first_chunk, dtype=np.int16).astype(np.float32)
                rms = float(np.sqrt(np.mean(samples * samples)))
                if rms > threshold:
                    is_speaking = True
                    speech_ms = self.FRAME_MS
                    audio_buffer.extend(first_chunk)

            while True:
                if (time.time() - start) > timeout_seconds:
                    if not is_speaking:
                        return None, None, None
                    break

                chunk = proc.stdout.read(frame_bytes)
                if not chunk:
                    err = (proc.stderr.read() or b"").decode("utf-8", errors="ignore").strip()
                    if err:
                        self.get_logger().error(f"Erro: pw-cat: {err}")
                    break

                samples = np.frombuffer(chunk, dtype=np.int16).astype(np.float32)
                rms = float(np.sqrt(np.mean(samples * samples)))

                if is_speaking:
                    audio_buffer.extend(chunk)
                    if rms < threshold:
                        silence_ms += self.FRAME_MS
                    else:
                        silence_ms = 0
                        speech_ms += self.FRAME_MS

                    if silence_ms >= self.END_SILENCE_MS and speech_ms >= self.MIN_SPEECH_MS:
                        break
                    elif total_ms >= self.MAX_RECORDING_MS:
                        break
                else:
                    if rms > threshold:
                        is_speaking = True
                        speech_ms = self.FRAME_MS
                        silence_ms = 0
                        audio_buffer.extend(chunk)

                total_ms += self.FRAME_MS

        except KeyboardInterrupt:
            audio_buffer = None
        finally:
            try:
                proc.terminate(); proc.wait(timeout=0.8)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

        if audio_buffer and len(audio_buffer) > 1000:
            return bytes(audio_buffer), rate, ch
        return None, None, None


    def save_wav(self, audio_data, filepath, sample_rate, channels):
        with wave.open(str(filepath), 'wb') as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data)

            
    def transcribe_audio(self, whisper_model: WhisperModel, audio_path):
        self.get_logger().info("Transcrevendo...")
        try:
            # palavras/expressões que o modelo deve reconhecer com mais precisão
            initial_prompt = ["Lisa"] + self.wake_words_ + self.voice_commands_
            initial_prompt = ", ".join(initial_prompt) # conversão da lista para string

            segments, info = whisper_model.transcribe(
                str(audio_path),
                language="pt",
                initial_prompt=initial_prompt,
                beam_size=5,
                best_of=1,
                temperature=0.0,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=200
                )
            )
            text = " ".join(seg.text.strip() for seg in segments)
            return text.strip() if text else None
        except Exception as e:
            self.get_logger().error(f"Erro: Transcription error: {e}")
            return None


    def record_fixed_seconds(self, seconds=3):
        if self.MIC_TARGET:
            self.get_logger().info(f"Using source target: {self.MIC_TARGET}")

        proc, rate, ch, first_chunk, err = self._select_record_pipeline(self.MIC_TARGET)
        if not proc:
            self.get_logger().error(f"Erro: {err}")
            return None, None, None

        bytes_per_sample = 2
        frame_bytes = int(rate * self.FRAME_MS / 1000) * bytes_per_sample * ch
        total_frames = int((seconds * 1000) / self.FRAME_MS)
        buf = bytearray()
        if first_chunk:
            buf.extend(first_chunk)

        try:
            for _ in range(total_frames - (1 if first_chunk else 0)):
                chunk = proc.stdout.read(frame_bytes)
                if not chunk:
                    err = (proc.stderr.read() or b"").decode("utf-8", errors="ignore").strip()
                    if err:
                        self.get_logger().error(f"Erro: pw-cat: {err}")
                    break
                buf.extend(chunk)
        finally:
            try:
                proc.terminate(); proc.wait(timeout=0.8)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

        return (bytes(buf), rate, ch) if buf else (None, None, None)

    def stt_loop(self):
        self.get_logger().info("Iniciando Speech to Text!")
  
        while rclpy.ok():
            try:
                # Modo de espera: escuta e transcreve a cada 2 segundos procurando a wake word
                self.get_logger().info("Esperando Wake Word...")
                audio_data, rate, ch = self.record_fixed_seconds(seconds=2)
                if audio_data:
                    self.save_wav(audio_data, self.TEMP_WAV, rate, ch)
                    text_detected = self.transcribe_audio(self.whisper_, self.TEMP_WAV)
                    if text_detected:
                        processed_text = unidecode(text_detected.lower()).replace(",","").replace("!","").replace("?","").replace("liza","lisa")
    
                        self.get_logger().info(f"Texto detectado (modo espera): '{text_detected}'!")
                        self.get_logger().info(f"Texto detectado processado (modo espera): '{processed_text}'!")
                        if any(wake_word in processed_text for wake_word in self.wake_words_):
                            # após detectar a wake word, entra em modo de escuta
                            # Modo de escuta: escuta por até 30 segundos e transcreve a frase
                            self.get_logger().info("Wake Word detectada!")
                            cmd_audio_data, cmd_rate, cmd_ch = self.record_with_vad(timeout_seconds=30)
                            if cmd_audio_data:
                                self.save_wav(cmd_audio_data, self.TEMP_WAV, sample_rate=cmd_rate, channels=cmd_ch)
                                cmd_text_detected = self.transcribe_audio(self.whisper_, self.TEMP_WAV)
                                if cmd_text_detected:
                                    self.get_logger().info(f"Frase detectada: \"{cmd_text_detected}\"\n")
                                    msg = String()
                                    msg.data = cmd_text_detected
                                    self.publisher_.publish(msg)
                                    time.sleep(self.AUTO_RESTART_DELAY)
                                else:
                                    self.get_logger().info("Nenhuma frase detectada\n")

                        else:
                            self.get_logger().info("Nenhuma Wake Word detectada.")

                    self.get_logger().info("Voltando para o modo de espera.\n")

            except KeyboardInterrupt:
                self.get_logger().info("\n\nInterrupted by user")
                break
            except Exception as e:
                self.get_logger().error(f"Erro: {e}")
                time.sleep(3)

def main(args=None):
    rclpy.init(args=args)
    node = VoiceCommandsDetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == "__main__":
    main()