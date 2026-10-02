# LISA 2026 — Docker

## 1. Pré-requisitos

Tenha instalado:

- Git
- Docker com `docker compose`

## 2. Clonar o projeto

```bash
git clone -b Joao-Lopes https://github.com/Grupo-SEMEAR-USP/LISA_2026.git
cd LISA_2026
```

## 3. Iniciar a LISA

Na primeira execução:

```bash
chmod +x Prog/docker/run_docker.sh
./Prog/docker/run_docker.sh --build
```

O script configura o acesso à câmera, áudio e tela e inicia o projeto automaticamente.

> O primeiro `--build` pode demorar bastante, principalmente na Raspberry Pi 5.

## 4. Próximas execuções

Depois que a imagem já foi criada:

```bash
cd LISA_2026
./Prog/docker/run_docker.sh
```

## 5. Parar a LISA

Pressione `Ctrl+C` no terminal onde ela estiver rodando.
