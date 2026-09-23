# LISA 2026 — Tutorial para executar com Docker

Este tutorial explica como uma pessoa externa pode baixar o projeto LISA 2026 e executá-lo usando Docker, sem precisar instalar ROS 2, Python, MediaPipe, OpenCV, Vosk ou outras dependências do projeto diretamente no sistema.

## 1. Pré-requisitos

O computador precisa ter:

- Ubuntu/Linux com Docker instalado
- Docker Compose disponível através do comando `docker compose`
- Git
- Uma câmera compatível com `/dev/video*`
- Microfone e saída de áudio, caso queira testar visão, voz e sons
- Ambiente gráfico com X11, caso queira visualizar os GIFs da LISA

> O projeto foi preparado e testado em Ubuntu 24.04.

### Verificar Docker

Execute:

```bash
docker --version
docker compose version
```

Se os dois comandos retornarem versões, o Docker está disponível.

Também verifique o Git:

```bash
git --version
```

---

## 2. Baixar o projeto

Clone a branch utilizada para o desenvolvimento:

```bash
git clone -b Joao-Lopes https://github.com/Grupo-SEMEAR-USP/LISA_2026.git
cd LISA_2026
```

A estrutura esperada na raiz é semelhante a:

```text
LISA_2026/
├── Dockerfile
├── docker-compose.yml
├── docker/
│   ├── entrypoint.sh
│   └── requirements.txt
└── Prog/
    ├── lisa_pkg/
    ├── lisa_interfaces/
    └── lisa_bringup/
```

---

## 3. Preparar o UID do usuário

O `docker-compose.yml` utiliza o UID do usuário para acessar o servidor de áudio do sistema.

Execute:

```bash
export USER_ID=$(id -u)
```

Esse comando precisa ser executado no mesmo terminal antes de iniciar o Docker.

Para conferir:

```bash
echo $USER_ID
```

Deve aparecer um número, por exemplo:

```text
1000
```

---

## 4. Permitir a interface gráfica

A LISA utiliza GIFs através da interface gráfica do computador.

Antes de iniciar o container, execute:

```bash
xhost +local:docker
```

Isso permite que o container acesse o servidor X11 local.

> Por segurança, esse acesso pode ser removido depois com:
>
> ```bash
> xhost -local:docker
> ```

---

## 5. Verificar a câmera

Confira se o sistema reconhece uma câmera:

```bash
ls -l /dev/video*
```

Normalmente aparecerá algo como:

```text
/dev/video0
/dev/video1
```

O container é executado com `privileged: true`, permitindo que os dispositivos de câmera sejam acessados.

---

## 6. Verificar o áudio

O Docker utiliza o servidor PulseAudio/PipeWire do sistema.

Antes de iniciar, é possível verificar se o áudio está funcionando no host:

```bash
pactl info
```

E listar os dispositivos:

```bash
aplay -l
arecord -l
```

O microfone utilizado pela LISA precisa estar disponível para o sistema.

---

## 7. Construir e executar a LISA

Na raiz do projeto:

```bash
docker compose up --build
```

Na primeira execução, o Docker irá:

1. Baixar a imagem base do ROS 2 Jazzy.
2. Instalar as dependências do sistema.
3. Instalar as dependências Python.
4. Copiar o código da LISA.
5. Compilar os pacotes ROS 2.
6. Iniciar o container.
7. Executar o launch principal da LISA.

A primeira execução pode demorar porque a imagem precisa ser construída.

---

## 8. Execuções seguintes

Depois que a imagem já foi construída, normalmente basta:

```bash
docker compose up
```

Se o código do projeto tiver sido alterado, o `docker-compose.yml` monta `./Prog` diretamente em `/lisa_ws/src`, então as alterações do código ficam disponíveis no container.

Se alguma alteração envolver o `Dockerfile`, `requirements.txt` ou dependências do sistema, será necessário reconstruir:

```bash
docker compose up --build
```

---

## 9. Parar a LISA

No terminal onde o Docker está rodando:

```text
Ctrl+C
```

Ou, em outro terminal dentro da pasta do projeto:

```bash
docker compose down
```

---

## 10. Verificar a configuração antes de executar

Se quiser verificar se o Docker Compose está interpretando corretamente o arquivo:

```bash
docker compose config
```

Se não houver erro, a configuração do Compose foi aceita.

---

## 11. Diagnóstico rápido

### Docker não encontrado

Se aparecer:

```text
docker: command not found
```

é necessário instalar o Docker no computador.

### `docker compose` não encontrado

Se aparecer algo como:

```text
docker: 'compose' is not a docker command
```

é necessário instalar/habilitar o Docker Compose.

### Nenhuma câmera encontrada

Confira:

```bash
ls -l /dev/video*
```

Se não aparecer nenhum dispositivo, verifique se a câmera está conectada e reconhecida pelo sistema.

### Problemas com a interface gráfica

Execute novamente:

```bash
xhost +local:docker
```

E confira:

```bash
echo $DISPLAY
```

O resultado normalmente será algo como:

```text
:0
```

### Problemas com áudio

Confira:

```bash
pactl info
aplay -l
arecord -l
```

Se o container não conseguir acessar o servidor de áudio, verifique se o PipeWire/PulseAudio está funcionando no host.

### Ver os logs do container

Com o container em execução:

```bash
docker compose logs -f
```

Para sair dos logs sem parar o container:

```text
Ctrl+C
```

### Abrir um terminal dentro do container

Com a LISA em execução:

```bash
docker exec -it lisa_2026 bash
```

Dentro do container, por exemplo:

```bash
source /opt/ros/jazzy/setup.bash
source /lisa_ws/install/setup.bash
ros2 node list
```

Para sair:

```bash
exit
```

---

## 12. Script de instalação/execução automática

Também existe o script `run_docker.sh` na raiz do projeto.

Ele automatiza:

- verificação do Docker;
- configuração do `USER_ID`;
- liberação do X11;
- verificação básica da câmera;
- construção da imagem;
- inicialização do Docker Compose.

Dê permissão de execução uma única vez:

```bash
chmod +x run_docker.sh
```

Depois:

```bash
./run_docker.sh
```

Para reconstruir a imagem:

```bash
./run_docker.sh --build
```

---

## 13. Fluxo recomendado para uma pessoa nova

Depois de instalar Docker e Git, o fluxo completo é:

```bash
git clone -b Joao-Lopes https://github.com/Grupo-SEMEAR-USP/LISA_2026.git
cd LISA_2026
chmod +x run_docker.sh
./run_docker.sh --build
```

Depois das próximas atualizações do código:

```bash
git pull
./run_docker.sh
```

Se houver alteração nas dependências ou no Dockerfile:

```bash
git pull
./run_docker.sh --build
```

---

## 14. Arquitetura do ambiente

O Docker fornece o ambiente de software da LISA:

```text
┌─────────────────────────────────────────┐
│              Computador                 │
│                                         │
│  Ubuntu + Docker                        │
│       │                                 │
│       ▼                                 │
│  ┌───────────────────────────────────┐  │
│  │          Container LISA           │  │
│  │                                   │  │
│  │  ROS 2 Jazzy                      │  │
│  │  Python                            │  │
│  │  OpenCV                            │  │
│  │  MediaPipe                         │  │
│  │  Vosk                              │  │
│  │  Nós ROS 2                         │  │
│  │                                   │  │
│  └───────────────────────────────────┘  │
│       │             │             │     │
│       ▼             ▼             ▼     │
│    Câmera         Áudio          GUI    │
│                                         │
└─────────────────────────────────────────┘
```

O código fonte continua no diretório `Prog/` do projeto e é montado no container em:

```text
/lisa_ws/src
```

---

## 15. Observações importantes

- O projeto utiliza ROS 2 Jazzy dentro do container.
- Não é necessário instalar ROS 2 Jazzy no host para executar a LISA.
- A câmera, áudio e interface gráfica continuam sendo recursos do computador host.
- O `network_mode: host` permite que o container utilize a rede do host.
- O container utiliza `privileged: true` para facilitar o acesso aos dispositivos de hardware necessários durante os testes.
- O projeto foi configurado principalmente para Linux/Ubuntu.
- O comportamento de câmera, áudio e interface gráfica pode variar dependendo do hardware e da configuração do sistema operacional.

---

## 16. Comandos resumidos

### Primeira execução

```bash
git clone -b Joao-Lopes https://github.com/Grupo-SEMEAR-USP/LISA_2026.git
cd LISA_2026
chmod +x run_docker.sh
./run_docker.sh --build
```

### Execução normal

```bash
cd LISA_2026
./run_docker.sh
```

### Atualizar o projeto

```bash
git pull
./run_docker.sh
```

### Rebuild completo da imagem

```bash
./run_docker.sh --build
```

### Parar

```bash
docker compose down
```

### Ver logs

```bash
docker compose logs -f
```

### Entrar no container

```bash
docker exec -it lisa_2026 bash
```
