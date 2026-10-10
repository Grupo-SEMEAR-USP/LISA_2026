#!/usr/bin/env bash

# ============================================================
# LISA v3 - Executar Docker
#
# Uso:
#   ./run_docker.sh
#   ./run_docker.sh --build
#   ./run_docker.sh --hide-cursor
#   ./run_docker.sh --build --hide-cursor
#
# Opções:
#   --build        Constrói ou reconstrói a imagem Docker sem iniciar a LISA.
#   --hide-cursor  Oculta temporariamente o cursor do GNOME.
#   --help         Exibe as opções disponíveis.
# ============================================================

set -euo pipefail

# ------------------------------------------------------------
# Configuração inicial e argumentos
# ------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BUILD=false
HIDE_CURSOR=false

# Processa os argumentos em qualquer ordem.
# A opção --help encerra o script antes de qualquer configuração
# de Docker, áudio, vídeo, display ou cursor.

while [ "$#" -gt 0 ]; do
    case "$1" in
        --build)
            BUILD=true
            ;;
        --hide-cursor)
            HIDE_CURSOR=true
            ;;
        --help|-h)
            printf '%s\n' \
                "Uso:" \
                "  ./run_docker.sh [--build] [--hide-cursor]" \
                "" \
                "Opções:" \
                "  --build        Constrói ou reconstrói a imagem Docker sem iniciar a LISA." \
                "  --hide-cursor  Oculta temporariamente o cursor." \
                "  --help, -h     Exibe esta mensagem."
            exit 0
            ;;
        *)
            printf 'ERRO: opção desconhecida: %s\n' "$1" >&2
            printf '%s\n' \
                "Use './run_docker.sh --help' para ver as opções." >&2
            exit 1
            ;;
    esac
    shift
done

if [ "$BUILD" = true ]; then
    HIDE_CURSOR=false
fi

# ------------------------------------------------------------
# Configuração do tema de cursor
# ------------------------------------------------------------
# O tema invisível é instalado no diretório pessoal do usuário,
# sem sudo. A configuração do GNOME só é alterada quando a
# opção --hide-cursor é informada.
#
# O tema original é guardado para ser restaurado ao encerrar
# o script, inclusive quando o usuário pressiona Ctrl+C.
# Um arquivo de recuperação permite restaurá-lo em execuções
# posteriores caso o script seja encerrado abruptamente.

CURSOR_THEME_NAME="LISA-Invisible"
CURSOR_THEME_DIR="${HOME}/.icons/${CURSOR_THEME_NAME}"
CURSOR_RECOVERY_FILE="${HOME}/.config/lisa-cursor-theme-backup"
CURSOR_THEME_ORIGINAL=""
CURSOR_THEME_CHANGED=false

# ------------------------------------------------------------
# Recuperação automática do cursor
# ------------------------------------------------------------
# Sem --hide-cursor, verifica se o tema invisível ficou ativo
# após uma execução anterior e tenta restaurar o tema original.
#
# A recuperação é feita antes das configurações do Docker.

recuperar_cursor() {
    # Verificar se há uma sessão GNOME acessível.
    if ! command -v gsettings >/dev/null 2>&1; then
        return 0
    fi

    local current_theme

    if ! current_theme="$(gsettings get org.gnome.desktop.interface cursor-theme 2>/dev/null)"; then
        return 0
    fi

    # Só recuperar automaticamente se o tema invisível estiver ativo.
    if [ "$current_theme" != "'${CURSOR_THEME_NAME}'" ] &&
       [ "$current_theme" != "\"${CURSOR_THEME_NAME}\"" ]; then
        return 0
    fi

    # Recuperar o tema original salvo pela execução anterior.
    if [ -s "$CURSOR_RECOVERY_FILE" ]; then
        local original_theme

        IFS= read -r original_theme < "$CURSOR_RECOVERY_FILE" || true

        if [ -n "$original_theme" ] &&
           [ "$original_theme" != "$CURSOR_THEME_NAME" ]; then
            if gsettings set org.gnome.desktop.interface cursor-theme \
                "$original_theme"; then
                rm -f "$CURSOR_RECOVERY_FILE"
                echo "Cursor restaurado para o tema: $original_theme"
                return 0
            fi

            echo "AVISO: não foi possível restaurar o tema original do cursor."
            echo "O backup foi mantido em: $CURSOR_RECOVERY_FILE"
            return 0
        fi
    fi

    # Sem backup válido, não presumir qual era o tema original.
    echo "AVISO: o cursor invisível está ativo, mas não há backup válido do tema original."
    echo "O tema não foi alterado para evitar substituir uma configuração personalizada."
}

# Sem a opção --hide-cursor, tentar recuperar uma execução anterior.
if [ "$HIDE_CURSOR" = false ]; then
    recuperar_cursor
fi

# ------------------------------------------------------------
# Verificar Docker e Docker Compose
# ------------------------------------------------------------

if ! command -v docker >/dev/null 2>&1; then
    echo "ERRO: Docker não está instalado ou não está no PATH."
    exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
    echo "ERRO: Docker Compose não está disponível."
    exit 1
fi

# ------------------------------------------------------------
# Identificação do usuário no host
# ------------------------------------------------------------
# Os IDs permitem executar o container com as permissões
# correspondentes ao usuário atual do sistema.

export USER_ID="$(id -u)"
export GROUP_ID="$(id -g)"
export USER_NAME="$(id -un)"

# ------------------------------------------------------------
# Configuração do display gráfico
# ------------------------------------------------------------
# O DISPLAY identifica o servidor gráfico utilizado pelo mpv.
# Em sessões locais, o valor costuma ser :0 ou :1.
# No Ubuntu com Wayland, aplicativos X11 utilizam o XWayland.

export DISPLAY="${DISPLAY:-:0}"

if [ ! -d /tmp/.X11-unix ]; then
    echo "AVISO: /tmp/.X11-unix não existe."
    echo "A interface gráfica pode não funcionar."
fi

# ------------------------------------------------------------
# Configuração do XAUTHORITY
# ------------------------------------------------------------
# O XAUTHORITY contém as credenciais de acesso ao servidor X11.
# São verificados, nesta ordem:
#   1. O arquivo indicado pela variável XAUTHORITY.
#   2. O arquivo ~/.Xauthority.
#   3. Um arquivo de autenticação do XWayland.
#
# Se nenhum for encontrado, é criado um arquivo temporário.
# Nesse caso, o acesso gráfico poderá depender do xhost.

TEMP_XAUTH=""

if [ -n "${XAUTHORITY:-}" ] && [ -f "${XAUTHORITY}" ]; then
    export XAUTHORITY_FILE="$XAUTHORITY"
elif [ -f "${HOME}/.Xauthority" ]; then
    export XAUTHORITY_FILE="${HOME}/.Xauthority"
else
    XWAYLAND_XAUTH=""

    if [ -d "/run/user/${USER_ID}" ]; then
        XWAYLAND_XAUTH="$(find "/run/user/${USER_ID}" \
            -maxdepth 1 \
            -type f \
            -name '.mutter-Xwaylandauth.*' \
            -print -quit 2>/dev/null || true)"
    fi

    if [ -n "$XWAYLAND_XAUTH" ] && [ -f "$XWAYLAND_XAUTH" ]; then
        export XAUTHORITY_FILE="$XWAYLAND_XAUTH"
    else
        TEMP_XAUTH="/tmp/lisa-docker-xauth-${USER_ID}"
        touch "$TEMP_XAUTH"
        chmod 600 "$TEMP_XAUTH"
        export XAUTHORITY_FILE="$TEMP_XAUTH"

        echo "AVISO: nenhum arquivo XAUTHORITY foi encontrado."
        echo "Tentando acesso ao X11/XWayland por xhost."
    fi
fi

# ------------------------------------------------------------
# Liberação temporária do acesso X11
# ------------------------------------------------------------
# O xhost é utilizado como alternativa quando necessário.
# O modo escolhido é registrado para que a permissão concedida
# seja removida durante a limpeza do script.

XHOST_MODE=""

if command -v xhost >/dev/null 2>&1; then
    export XAUTHORITY="$XAUTHORITY_FILE"

    if xhost +SI:localuser:"$USER_NAME" >/dev/null 2>&1; then
        XHOST_MODE="localuser"
    elif xhost +local:docker >/dev/null 2>&1; then
        XHOST_MODE="docker"
    else
        echo "AVISO: não foi possível liberar o acesso X11 com xhost."
    fi
fi

# ------------------------------------------------------------
# Configuração de áudio: PulseAudio / PipeWire
# ------------------------------------------------------------
# O container utiliza o socket de áudio da sessão do usuário.
# O diretório de configuração também pode disponibilizar o
# cookie necessário para autenticação do áudio.

export VIDEO_GID="$(getent group video | cut -d: -f3)"

export PULSE_SOCKET_DIR="/run/user/${USER_ID}/pulse"
export PULSE_CONFIG_DIR="${HOME}/.config/pulse"

mkdir -p "$PULSE_CONFIG_DIR"

if [ ! -S "${PULSE_SOCKET_DIR}/native" ]; then
    echo "AVISO: socket ${PULSE_SOCKET_DIR}/native não encontrado."
    echo "O detector_comandos_de_voz poderá iniciar sem microfone funcional."
fi

# ------------------------------------------------------------
# Verificação da câmera
# ------------------------------------------------------------
# Apenas verifica se há dispositivos de vídeo disponíveis.
# A disponibilização efetiva da câmera depende da configuração
# do Docker Compose.

if ! compgen -G "/dev/video*" > /dev/null; then
    echo "AVISO: nenhuma câmera /dev/video* encontrada."
fi

# ------------------------------------------------------------
# Limpeza ao encerrar
# ------------------------------------------------------------
# Executada ao terminar normalmente ou após interrupções
# tratadas pelo script.
#
# Responsabilidades:
#   - Restaurar o tema de cursor, se ele foi alterado.
#   - Manter o backup caso a restauração falhe.
#   - Remover a permissão X11 concedida pelo xhost.
#   - Excluir o arquivo XAUTHORITY temporário, se criado.

cleanup() {
    # Restaurar o tema original do GNOME somente se necessário.
    if [ "$CURSOR_THEME_CHANGED" = true ]; then
        if gsettings set org.gnome.desktop.interface cursor-theme \
            "$CURSOR_THEME_ORIGINAL"; then
            rm -f "$CURSOR_RECOVERY_FILE"
        else
            echo "AVISO: não foi possível restaurar o tema original do cursor."
            echo "O backup foi mantido em: $CURSOR_RECOVERY_FILE"
            echo "Restaure manualmente com:"
            echo "  gsettings set org.gnome.desktop.interface cursor-theme \"$CURSOR_THEME_ORIGINAL\""
        fi

        CURSOR_THEME_CHANGED=false
    fi

    # Revogar a permissão X11 concedida anteriormente.
    if command -v xhost >/dev/null 2>&1; then
        case "$XHOST_MODE" in
            localuser)
                xhost -SI:localuser:"$USER_NAME" >/dev/null 2>&1 || true
                ;;
            docker)
                xhost -local:docker >/dev/null 2>&1 || true
                ;;
        esac
    fi

    # Remover somente o arquivo temporário criado pelo script.
    if [ -n "$TEMP_XAUTH" ]; then
        rm -f "$TEMP_XAUTH"
    fi
}

# ------------------------------------------------------------
# Instalar e ativar cursor invisível
# ------------------------------------------------------------
# Esta função só será chamada com --hide-cursor.
#
# O tema é baixado e instalado em ~/.icons caso ainda não exista.
# Depois, o tema atual do GNOME é guardado e substituído pelo
# tema invisível. A restauração é feita pela função cleanup.

ativar_cursor_invisivel() {
    # Verificar se há uma sessão GNOME acessível.
    if ! command -v gsettings >/dev/null 2>&1 ||
       ! gsettings get org.gnome.desktop.interface cursor-theme \
            >/dev/null 2>&1; then
        echo "AVISO: sessão GNOME indisponível; cursor não alterado."
        return 0
    fi

    # Baixar e instalar o tema apenas se ele não estiver completo.
    if [ ! -f "${CURSOR_THEME_DIR}/cursors/left_ptr" ]; then
        if ! command -v curl >/dev/null 2>&1 ||
           ! command -v tar >/dev/null 2>&1; then
            echo "AVISO: curl e tar são necessários para instalar o cursor."
            return 0
        fi

        local temp_dir
        temp_dir="$(mktemp -d)" || return 0

        echo "Instalando o tema de cursor invisível..."

        if ! curl -fsSL \
            "https://github.com/andcor02/transparent-xcursor-linux/archive/refs/heads/master.tar.gz" \
            | tar -xz --strip-components=1 -C "$temp_dir"; then
            echo "AVISO: não foi possível baixar o tema do cursor."
            rm -rf "$temp_dir"
            return 0
        fi

        if [ ! -d "${temp_dir}/cursors" ]; then
            echo "AVISO: arquivos de cursor não encontrados no download."
            rm -rf "$temp_dir"
            return 0
        fi

        mkdir -p "$HOME/.icons"

        # Recriar somente o diretório reservado a este tema.
        rm -rf "$CURSOR_THEME_DIR"
        mkdir -p "$CURSOR_THEME_DIR"

        if ! cp -a "${temp_dir}/cursors" "$CURSOR_THEME_DIR/"; then
            echo "AVISO: não foi possível instalar os arquivos do cursor."
            rm -rf "$temp_dir" "$CURSOR_THEME_DIR"
            return 0
        fi

        # Registrar os metadados do tema para o GNOME/Xcursor.
        cat > "${CURSOR_THEME_DIR}/index.theme" <<'EOF'
[Icon Theme]
Name=LISA Invisible
Comment=Transparent cursor theme for LISA
EOF

        rm -rf "$temp_dir"
    fi

    # Guardar o tema atualmente selecionado.
    local current_theme

    if ! current_theme="$(gsettings get org.gnome.desktop.interface cursor-theme)"; then
        echo "AVISO: não foi possível identificar o tema atual do cursor."
        return 0
    fi

    CURSOR_THEME_ORIGINAL="$(
        printf '%s' "$current_theme" |
        sed -e "s/^'//" -e "s/'$//"
    )"

    if [ -z "$CURSOR_THEME_ORIGINAL" ]; then
        echo "AVISO: não foi possível identificar o tema original."
        return 0
    fi

    # Salvar o tema original para permitir recuperação após
    # encerramento abrupto do script.
    mkdir -p "$(dirname "$CURSOR_RECOVERY_FILE")"

    if ! printf '%s\n' "$CURSOR_THEME_ORIGINAL" > "$CURSOR_RECOVERY_FILE"; then
        echo "AVISO: não foi possível salvar o backup do tema do cursor."
        return 0
    fi

    # Ativar o tema invisível e registrar a alteração para cleanup.
    if gsettings set org.gnome.desktop.interface cursor-theme \
        "$CURSOR_THEME_NAME"; then
        CURSOR_THEME_CHANGED=true
        echo "Cursor invisível ativado para a LISA."
    else
        echo "AVISO: não foi possível ativar o tema de cursor."
        rm -f "$CURSOR_RECOVERY_FILE"
    fi
}

# ------------------------------------------------------------
# Registro dos mecanismos de limpeza
# ------------------------------------------------------------
# EXIT executa a limpeza ao sair.
# INT e TERM convertem as interrupções em saídas normais, para
# que o trap de EXIT também possa executar a limpeza.

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# ------------------------------------------------------------
# Ativação opcional do cursor invisível
# ------------------------------------------------------------
# Com --hide-cursor, ativa o tema invisível.
# Sem a opção, a recuperação automática já foi tentada no início.

if [ "$HIDE_CURSOR" = true ]; then
    ativar_cursor_invisivel
fi

# ------------------------------------------------------------
# Inicialização da LISA
# ------------------------------------------------------------
# Com --build, constrói a imagem sem iniciar os contêineres.
# Caso contrário, inicia os serviços da LISA normalmente.

echo
echo "=============================================="
echo "             LISA v3 - Docker"
echo "=============================================="
echo

if [ "$BUILD" = true ]; then
    echo "Construindo a imagem Docker da LISA..."
    docker compose build
    echo
    echo "Imagem construída com sucesso!"
    echo
    exit 0
fi

docker compose up
