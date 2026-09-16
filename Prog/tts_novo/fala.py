"""
sintese de voz usando Piper (100% offline).
"""

import os
import subprocess
import tempfile
import config


def falar(texto):
    """
    gera audio a partir do texto usando Piper e toca no alto-falante.
    usa arquivo temporario unico por chamada, pra evitar conflito
    se por algum motivo duas chamadas acontecerem quase juntas.
    """
    if not texto or not texto.strip():
        return

    texto_limpo = texto.replace('%', ' por cento').replace('\n', ' ').strip()
    print(f"IA: {texto_limpo}")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        arquivo_audio = tmp.name

    comando_piper = ["piper", "--model", config.MODELO_VOZ, "--output_file", arquivo_audio]

    try:
        subprocess.run(
            comando_piper,
            input=texto_limpo,
            capture_output=True,
            text=True,
            check=True,
        )

        if os.path.exists(arquivo_audio) and os.path.getsize(arquivo_audio) > 100:
            subprocess.run(
                ["aplay", "-q", arquivo_audio],
                check=True,
                stderr=subprocess.DEVNULL,
            )
        else:
            print("Erro: o Piper gerou um arquivo vazio ou muito pequeno.")

    except subprocess.CalledProcessError as e:
        stderr_msg = e.stderr if hasattr(e, "stderr") and e.stderr else str(e)
        print(f"Falha ao gerar ou tocar audio: {stderr_msg}")
    except Exception as e:
        print(f"Erro ao tentar reproduzir o audio: {e}")
    finally:
        if os.path.exists(arquivo_audio):
            os.remove(arquivo_audio)
