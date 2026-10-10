# Tutorial de utilização do Docker da LISA v3

## Pré-requisitos

- Git
- Docker com `docker compose`

## Primeira execução

Clonar o projeto:

```bash
git clone https://github.com/Grupo-SEMEAR-USP/LISA_2026.git
cd LISA_2026
```

Na primeira execução, utilize a flag `--build` para construir a imagem Docker:

```bash
chmod +x Prog/docker/*.sh
./Prog/docker/run_docker.sh --build
```
> Obs: O primeiro `--build` pode demorar bastante.

## Próximas execuções

Depois que a imagem já foi criada, utilize o script sem a flag `--build`. Ele configura o acesso à câmera, áudio e tela e inicia o projeto automaticamente:

```bash
cd LISA_2026
./Prog/docker/run_docker.sh
```

## Ocultar o cursor

Para esconder o cursor do sistema ao iniciar a LISA utilize a flag `--hide-cursor`:

```bash
cd LISA_2026
./Prog/docker/run_docker.sh --hide-cursor
```

Essa opção deixa o cursor invisível no ambiente gráfico do computador enquanto a LISA está em execução, proporcionando uma experiência mais imersiva. 

Utilizando essa flag, o cursor será oculto em todo o sistema, e não só na LISA. Ao encerrar o script normalmente, o cursor original é restaurado automaticamente. 

Caso ocorra algum erro e o cursor permaneça invisível mesmo após finalizar a execução da LISA, execute novamente o script sem a flag --hide-cursor, pois ele tentará restaurar o tema original automaticamente.

## Acessar o terminal do contêiner da LISA

Para debug e inspeção do ambiente ROS 2 (visualizar os nós, tópicos, mensagens, serviços, etc) é necessário acessar o terminal interno do contêiner, caso seu computador não tenha o ROS 2 instalado. 

Com a LISA em execução, abra outro terminal e execute:

```bash
cd LISA_2026
./Prog/docker/acessar_docker.sh
```

A partir desse terminal, você poderá utilizar os comandos ROS 2 disponíveis no ambiente do contêiner para inspecionar e depurar o projeto.