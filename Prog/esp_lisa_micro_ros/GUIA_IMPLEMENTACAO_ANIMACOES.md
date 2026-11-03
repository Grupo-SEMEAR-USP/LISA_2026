# Guia de implementação de animações da LISA

**Público-alvo:** integrantes responsáveis pelo firmware da ESP32\
**Objetivo:** ensinar a criar uma nova animação composta por movimentos
de um ou mais servos, sem precisar conhecer ROS 2 ou micro-ROS.

------------------------------------------------------------------------

## 1. Visão geral

Na LISA, uma **animação** é uma sequência coordenada de movimentos de um
ou mais motores. Por exemplo:

-   `dancinha`: alternar posições de braços e cabeça em uma sequência;
-   `mimica`: acompanhar uma sequência de gestos com os braços e o
    pescoço;
-   `acenar`: movimentar um braço repetidamente;
-   `olhar_lados`: girar o pescoço para a esquerda e para a direita.

O firmware recebe uma solicitação de animação por meio da infraestrutura
de comunicação já implementada. **A implementação da animação não
precisa conhecer ROS, tópicos, serviços ou mensagens.** Ela só precisa
controlar os motores usando a interface de hardware disponibilizada pelo
firmware.

A comunicação e a execução dos movimentos são responsabilidades
separadas:

1.  A camada de comunicação recebe uma solicitação.
2.  O gerenciador de animações verifica se já existe uma animação em
    execução.
3.  Se estiver livre, o gerenciador inicia a animação solicitada.
4.  O `loop()` do firmware chama periodicamente a atualização da
    animação.
5.  Quando a rotina termina, o gerenciador libera a execução para a
    próxima solicitação.

Este documento trata somente da etapa 3 a 5: **como implementar uma nova
animação**.

### 1.1 Regra mais importante: animações não podem bloquear o firmware

O firmware precisa continuar executando seu `loop()` enquanto os motores
se movimentam. Isso permite que a placa atualize os motores, verifique o
término da animação e continue atendendo às demais tarefas do firmware.

Por isso, não use esperas bloqueantes como:

``` cpp
delay(1000);

while (motor_nao_chegou_na_posicao) {
    // espera
}
```

Também evite laços `for` ou `while` que tentem executar toda a sequência
de movimentos de uma vez.

Em vez disso, a animação deve avançar **um pequeno passo por chamada**,
usando `millis()` para controlar o tempo. O `loop()` chama a função de
atualização repetidamente, e ela decide se já chegou a hora de executar
a próxima etapa.

------------------------------------------------------------------------

## 2. Estrutura dos arquivos

A organização sugerida para o firmware é:

``` text
esp_lisa_micro_ros/
├── esp_lisa_micro_ros.ino
├── animacoes/
│   ├── animacoes.h
│   ├── dancinha.cpp
│   ├── mimica.cpp
│   ├── acenar.cpp
│   └── ...
└── hardware/
    ├── motores.h
    └── motores.cpp
```

Responsabilidade de cada parte:

  -----------------------------------------------------------------------
  Arquivo                             Responsabilidade
  ----------------------------------- -----------------------------------
  `esp_lisa_micro_ros.ino`         Firmware principal. Mantém o
                                      `loop()` e a comunicação.

  `animacoes/animacoes.h`             Declara as funções públicas das
                                      animações e, se adotado, a
                                      interface comum.

  `animacoes/dancinha.cpp`            Implementa somente a sequência de
                                      movimentos da dancinha.

  `animacoes/mimica.cpp`              Implementa somente a sequência de
                                      movimentos da mímica.

  `hardware/motores.h`                Declara as funções disponibilizadas
                                      para controlar os motores.

  `hardware/motores.cpp`              Implementa o controle físico dos
                                      servos.
  -----------------------------------------------------------------------

Cada nova animação deve ficar em seu próprio arquivo `.cpp`. Assim, uma
pessoa pode desenvolver `acenar.cpp` sem precisar alterar a
implementação de `dancinha.cpp`.

> **Importante:** os nomes e as funções reais de `hardware/motores.h`
> devem ser combinados com a pessoa responsável pelo hardware. Os
> exemplos deste guia usam uma interface ilustrativa; não presuma que
> ela já existe no repositório.

------------------------------------------------------------------------

## 3. Interface que toda animação deve seguir

Para que o gerenciador consiga executar animações diferentes de maneira
uniforme, cada animação deve oferecer quatro funções:

``` cpp
void iniciar_NOME();
void atualizar_NOME();
void finalizar_NOME();
bool NOME_em_execucao();
```

Substitua `NOME` pelo nome da animação. Para a animação `acenar`, por
exemplo:

``` cpp
void iniciar_acenar();
void atualizar_acenar();
void finalizar_acenar();
bool acenar_em_execucao();
```

### 3.1 `iniciar_NOME()`

É chamada uma única vez quando a animação começa.

Deve:

-   inicializar o estado interno da animação;
-   definir qual é a primeira etapa;
-   registrar o instante inicial com `millis()`;
-   enviar os motores para a primeira posição, se necessário.

Não deve conter esperas ou executar a sequência inteira.

### 3.2 `atualizar_NOME()`

É chamada repetidamente pelo `loop()` enquanto a animação está ativa.

Deve:

-   verificar se já passou o tempo necessário para a próxima etapa;
-   executar apenas a etapa que estiver pronta;
-   atualizar o estado interno;
-   marcar a animação como concluída quando chegar ao fim.

Essa função precisa ser rápida. Se ainda não chegou a hora de fazer
algo, deve simplesmente retornar.

### 3.3 `finalizar_NOME()`

É chamada quando a animação termina ou quando o firmware precisa
interrompê-la.

Deve:

-   colocar os motores em uma condição segura ou definida pelo projeto;
-   limpar o estado interno;
-   garantir que a animação seja considerada encerrada.

A posição final dos servos deve ser uma decisão consciente. Em alguns
casos, faz sentido voltar à posição neutra; em outros, manter a última
posição é desejável. Combine esse comportamento com a equipe.

### 3.4 `NOME_em_execucao()`

Retorna:

-   `true` enquanto a animação ainda estiver em andamento;
-   `false` depois que ela terminar ou for finalizada.

O gerenciador usa essa informação para saber quando pode liberar a
execução.

------------------------------------------------------------------------

## 4. Como representar uma sequência de movimentos

Uma animação deve ser dividida em **etapas**. Cada etapa define:

1.  quais motores devem se movimentar;
2.  para quais posições;
3.  quanto tempo esperar antes de avançar para a próxima etapa.

Exemplo conceitual de uma animação:

  Etapa     Braço esquerdo   Braço direito   Pescoço   Duração da etapa
  ------- ---------------- --------------- --------- ------------------
  1                    40°            140°       90°             700 ms
  2                    90°             90°       60°             500 ms
  3                   140°             40°      120°             700 ms
  4                    90°             90°       90°             500 ms

Os valores são apenas ilustrativos. Os limites reais dependem da
montagem mecânica e da calibração de cada servo.

A sequência pode ser representada por um `enum`:

``` cpp
enum EtapaAcenar {
    POSICAO_INICIAL,
    BRACO_LEVANTADO,
    ACENO_1,
    ACENO_2,
    VOLTAR,
    CONCLUIDA
};
```

E o estado atual fica armazenado em uma variável:

``` cpp
static EtapaAcenar etapa_atual = CONCLUIDA;
```

O `static` mantém o valor entre chamadas de `atualizar_acenar()`. Sem
isso, a variável seria recriada a cada chamada e a animação perderia seu
progresso.

------------------------------------------------------------------------

## 5. Exemplo completo: animação `acenar`

Este exemplo demonstra a estrutura. Ele pressupõe que exista uma
interface de hardware semelhante a:

``` cpp
// Exemplo ilustrativo de hardware/motores.h
void mover_servo(int id_servo, int angulo);
```

A implementação real dessa função é responsabilidade da camada de
hardware. Ela deve enviar o comando ao servo sem introduzir esperas
bloqueantes.

### 5.1 Arquivo `animacoes/acenar.cpp`

``` cpp
#include <Arduino.h>
#include "animacoes.h"
#include "../hardware/motores.h"

// Identificador ilustrativo do servo do braço direito.
// Use os identificadores definidos em hardware/motores.h.
#define SERVO_BRACO_DIREITO 0

// Tempo entre as etapas da animação.
static const unsigned long TEMPO_ETAPA_MS = 400;

// Estados possíveis da animação.
enum EtapaAcenar {
    POSICAO_INICIAL,
    BRACO_LEVANTADO,
    ACENO_ESQUERDA,
    ACENO_DIREITA,
    VOLTAR,
    CONCLUIDA
};

// Estado atual e instante em que a etapa começou.
static EtapaAcenar etapa_atual = CONCLUIDA;
static unsigned long instante_etapa = 0;


// ------------------------------------------------------------
// Inicia a animação
// ------------------------------------------------------------

void iniciar_acenar() {
    etapa_atual = POSICAO_INICIAL;
    instante_etapa = millis();

    // Coloca o braço na posição inicial.
    mover_servo(SERVO_BRACO_DIREITO, 90);
}


// ------------------------------------------------------------
// Atualiza a animação
// Deve ser chamada repetidamente pelo loop().
// ------------------------------------------------------------

void atualizar_acenar() {

    // Não há nada para atualizar se a animação terminou.
    if (etapa_atual == CONCLUIDA) {
        return;
    }

    // Aguarda sem bloquear o loop.
    // A subtração também funciona corretamente quando millis()
    // sofre rollover, desde que os intervalos sejam curtos.
    if (millis() - instante_etapa < TEMPO_ETAPA_MS) {
        return;
    }

    // Registra o início da nova etapa.
    instante_etapa = millis();

    switch (etapa_atual) {

        case POSICAO_INICIAL:
            mover_servo(SERVO_BRACO_DIREITO, 150);
            etapa_atual = BRACO_LEVANTADO;
            break;

        case BRACO_LEVANTADO:
            mover_servo(SERVO_BRACO_DIREITO, 120);
            etapa_atual = ACENO_ESQUERDA;
            break;

        case ACENO_ESQUERDA:
            mover_servo(SERVO_BRACO_DIREITO, 150);
            etapa_atual = ACENO_DIREITA;
            break;

        case ACENO_DIREITA:
            mover_servo(SERVO_BRACO_DIREITO, 120);
            etapa_atual = VOLTAR;
            break;

        case VOLTAR:
            mover_servo(SERVO_BRACO_DIREITO, 90);
            etapa_atual = CONCLUIDA;
            break;

        case CONCLUIDA:
            break;
    }
}


// ------------------------------------------------------------
// Finaliza a animação
// ------------------------------------------------------------

void finalizar_acenar() {
    mover_servo(SERVO_BRACO_DIREITO, 90);
    etapa_atual = CONCLUIDA;
}


// ------------------------------------------------------------
// Informa se a animação ainda está em execução
// ------------------------------------------------------------

bool acenar_em_execucao() {
    return etapa_atual != CONCLUIDA;
}
```

### 5.2 Arquivo `animacoes/animacoes.h`

Adicione as declarações públicas da animação:

``` cpp
#ifndef ANIMACOES_H
#define ANIMACOES_H

void iniciar_acenar();
void atualizar_acenar();
void finalizar_acenar();
bool acenar_em_execucao();

#endif
```

Se o projeto já tiver esse arquivo, acrescente as declarações sem apagar
as existentes.

### 5.3 O que acontece durante a execução?

1.  `iniciar_acenar()` posiciona o braço e registra o horário inicial.
2.  O `loop()` chama `atualizar_acenar()` repetidamente.
3.  Antes de completar 400 ms, a função retorna imediatamente.
4.  Depois de 400 ms, a função envia o próximo comando e avança uma
    etapa.
5.  Esse processo se repete até a etapa `CONCLUIDA`.
6.  `acenar_em_execucao()` passa a retornar `false`.

Observe que o exemplo não espera o servo chegar fisicamente à posição.
Ele envia um comando e avança após o intervalo definido. Se o projeto
precisar confirmar a posição real, será necessário implementar
leitura/feedback do servo ou ajustar os tempos de acordo com os testes
mecânicos.

------------------------------------------------------------------------

## 6. Movimentando vários servos na mesma etapa

Uma etapa pode comandar vários servos. Basta enviar os comandos na mesma
chamada de atualização:

``` cpp
case POSICAO_INICIAL:
    mover_servo(SERVO_BRACO_ESQUERDO, 40);
    mover_servo(SERVO_BRACO_DIREITO, 140);
    mover_servo(SERVO_PESCOCO, 90);

    etapa_atual = PROXIMA_ETAPA;
    break;
```

Isso inicia os comandos praticamente no mesmo instante. A movimentação
física simultânea depende de como a camada de hardware controla os
servos.

**Não** faça isto:

``` cpp
mover_servo(SERVO_BRACO_ESQUERDO, 40);
delay(500);
mover_servo(SERVO_BRACO_DIREITO, 140);
```

Esse padrão bloqueia o firmware e ainda faz os movimentos começarem em
momentos diferentes.

------------------------------------------------------------------------

## 7. Movimento gradual: posição-alvo e interpolação

Enviar um ângulo ao servo normalmente define uma **posição-alvo**.
Dependendo da biblioteca e do hardware, o servo pode tentar chegar até
ela na velocidade própria do motor.

Se for necessário controlar a velocidade, pode-se implementar movimento
gradual: em vez de saltar diretamente de 90° para 150°, aumentar o
ângulo aos poucos.

Exemplo conceitual:

``` cpp
angulo_atual += 1;
mover_servo(SERVO_BRACO_DIREITO, angulo_atual);
```

Esse incremento deve ocorrer somente quando chegar o instante da próxima
atualização, também controlado com `millis()`.

Uma alternativa é interpolar entre posição inicial e final durante uma
duração definida:

$$
angulo(t) = angulo_{inicial} + \frac{t}{T}(angulo_{final} - angulo_{inicial})
$$

em que `t` é o tempo decorrido e `T` é a duração total do movimento. Ao
atingir `T`, o ângulo deve ser exatamente o alvo.

Para uma animação com vários servos, cada servo pode ter seu próprio
ângulo inicial e final, mas compartilhar o mesmo tempo de movimento.
Isso permite que braços e pescoço se movimentem de forma coordenada.

A interpolação deve respeitar os limites mecânicos e os limites
configurados para cada servo. Não assuma que todo servo pode operar com
segurança entre 0° e 180°.

------------------------------------------------------------------------

## 8. Repetições e animações em loop

Algumas animações precisam repetir um movimento algumas vezes. Há duas
maneiras comuns:

### Repetição com contador

``` cpp
static int repeticoes = 0;

case FIM_DO_CICLO:
    repeticoes++;

    if (repeticoes < 3) {
        etapa_atual = INICIO_DO_CICLO;
    } else {
        etapa_atual = CONCLUIDA;
    }
    break;
```

Zere o contador em `iniciar_NOME()`:

``` cpp
repeticoes = 0;
```

### Repetição contínua

Se a animação precisar continuar até ser interrompida, não marque
`CONCLUIDA` ao final do ciclo. Volte para a primeira etapa.

Nesse caso, `NOME_em_execucao()` continuará retornando `true` até que
`finalizar_NOME()` seja chamada.

Combine previamente se uma animação é finita ou contínua. Animações
contínuas precisam ter uma forma clara de interrupção.

------------------------------------------------------------------------

## 9. Regras de segurança e boas práticas

Antes de entregar uma animação, confira os seguintes pontos:

### Movimento e limites

-   [ ] Todos os ângulos estão dentro dos limites mecânicos do robô.
-   [ ] Os movimentos não forçam braços, articulações, cabos ou
    estruturas.
-   [ ] As posições iniciais e finais foram testadas com cuidado.
-   [ ] A animação não presume que todos os servos têm a mesma
    orientação ou calibração.
-   [ ] Movimentos simultâneos não causam colisões entre peças.

### Execução não bloqueante

-   [ ] Não existe `delay()` na animação.
-   [ ] Não existem laços `while` esperando motor ou tempo.
-   [ ] Cada chamada de `atualizar_NOME()` executa rapidamente e
    retorna.
-   [ ] O tempo é controlado com `millis()` ou mecanismo não bloqueante
    equivalente.
-   [ ] A animação não executa toda a sequência dentro de
    `iniciar_NOME()`.

### Estado e encerramento

-   [ ] O estado inicial é configurado em `iniciar_NOME()`.
-   [ ] `NOME_em_execucao()` retorna `true` durante toda a execução.
-   [ ] Ao terminar, a animação passa a retornar `false`.
-   [ ] `finalizar_NOME()` interrompe a sequência e deixa os motores em
    uma condição definida.
-   [ ] Contadores, temporizadores e variáveis de estado são
    reinicializados ao iniciar novamente.

### Organização

-   [ ] A animação está em seu próprio arquivo `.cpp`.
-   [ ] As funções públicas estão declaradas em `animacoes.h`.
-   [ ] O código usa a interface de `hardware/motores.h`, em vez de
    duplicar o controle dos servos.
-   [ ] A animação não contém código de ROS 2 ou micro-ROS.
-   [ ] Os nomes das funções seguem o padrão definido neste guia.

------------------------------------------------------------------------

## 10. Erros comuns

  -----------------------------------------------------------------------
  Problema                Causa provável          Como corrigir
  ----------------------- ----------------------- -----------------------
  O micro-ROS para de     Uso de `delay()` ou     Transformar a rotina em
  responder durante a     laço de espera          etapas não bloqueantes.
  animação                                        

  A animação sempre volta Variável de estado      Usar variável `static`
  para a primeira etapa   local comum, recriada a ou estado persistente
                          cada chamada            da animação.

  A animação nunca        Estado final não é      Verificar as transições
  termina                 alcançado ou a função   e retornar `false` no
                          de consulta está        estado final.
                          incorreta               

  A animação não reinicia Temporizadores ou       Reinicializar todo o
  corretamente            contadores não são      estado em
                          reinicializados         `iniciar_NOME()`.

  Os movimentos ficam     Cada servo é comandado  Enviar os comandos da
  fora de sincronia       em momentos diferentes  mesma etapa juntos e
                          ou há esperas           controlar o tempo
                          bloqueantes             centralmente.

  O servo se move de      Salto grande entre      Usar interpolação ou
  forma brusca            posições-alvo           limitar a velocidade do
                                                  movimento.

  O mecanismo força ou    Ângulo fora da faixa    Reduzir os limites e
  bate no fim de curso    mecânica ou calibração  testar cada articulação
                          incorreta               com cuidado.
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 11. Como criar uma nova animação: passo a passo

Para implementar, por exemplo, uma animação chamada `dancinha`:

1.  **Defina a sequência:** descreva em uma tabela as etapas, os servos
    envolvidos, os ângulos e os intervalos.
2.  **Confira os motores disponíveis:** consulte `hardware/motores.h`
    para saber os identificadores e as funções de controle.
3.  **Crie `animacoes/dancinha.cpp`:** implemente as quatro funções
    `iniciar_dancinha()`, `atualizar_dancinha()`, `finalizar_dancinha()`
    e `dancinha_em_execucao()`.
4.  **Declare as funções:** adicione as declarações em
    `animacoes/animacoes.h`.
5.  **Implemente por etapas:** use uma variável de estado e `millis()`;
    não use esperas bloqueantes.
6.  **Teste os limites:** inicialmente, teste com movimentos pequenos e
    sem pessoas próximas às partes móveis.
7.  **Teste o término:** confirme que a função de consulta retorna
    `false` no final.
8.  **Teste a interrupção:** confirme que `finalizar_dancinha()`
    interrompe a sequência de forma segura.
9.  **Integre ao gerenciador:** informe à pessoa responsável pelo
    gerenciador quais são as funções públicas da animação. A integração
    com a comunicação não faz parte deste guia.

### Modelo para copiar

Use este esqueleto ao iniciar uma nova animação. Substitua `NOME` pelo
nome escolhido e implemente as etapas:

``` cpp
#include <Arduino.h>
#include "animacoes.h"
#include "../hardware/motores.h"

enum EtapaNOME {
    ETAPA_INICIAL,
    ETAPA_2,
    ETAPA_3,
    CONCLUIDA
};

static EtapaNOME etapa_atual = CONCLUIDA;
static unsigned long instante_etapa = 0;

void iniciar_NOME() {
    etapa_atual = ETAPA_INICIAL;
    instante_etapa = millis();

    // Configure a posição inicial dos motores.
}

void atualizar_NOME() {
    if (etapa_atual == CONCLUIDA) {
        return;
    }

    if (millis() - instante_etapa < 500) {
        return;
    }

    instante_etapa = millis();

    switch (etapa_atual) {
        case ETAPA_INICIAL:
            // Comande um ou mais motores.
            etapa_atual = ETAPA_2;
            break;

        case ETAPA_2:
            // Comande o próximo movimento.
            etapa_atual = ETAPA_3;
            break;

        case ETAPA_3:
            // Último movimento.
            etapa_atual = CONCLUIDA;
            break;

        case CONCLUIDA:
            break;
    }
}

void finalizar_NOME() {
    // Interrompa a sequência e deixe os motores em condição segura.
    etapa_atual = CONCLUIDA;
}

bool NOME_em_execucao() {
    return etapa_atual != CONCLUIDA;
}
```

No esqueleto, substitua `NOME` pelo mesmo identificador em todos os
lugares. Por exemplo, para `dancinha`, use `EtapaDancinha`,
`iniciar_dancinha()`, `atualizar_dancinha()`, `finalizar_dancinha()` e
`dancinha_em_execucao()`.

------------------------------------------------------------------------

## 12. O que a pessoa responsável pela animação precisa entregar

Para cada nova animação, entregue:

1.  O arquivo `animacoes/NOME.cpp`.
2.  As declarações correspondentes em `animacoes/animacoes.h`.
3.  Uma breve descrição da sequência de movimentos, incluindo os servos
    utilizados, ângulos e tempos.
4.  A confirmação de que a animação não usa esperas bloqueantes.
5.  O resultado dos testes de início, execução, término e interrupção.

**Resumo:** a pessoa que implementa uma animação não precisa conhecer
ROS 2 nem alterar a comunicação da ESP32. Ela precisa conhecer a
interface de controle dos motores, implementar uma sequência de etapas
não bloqueantes e respeitar as quatro funções padronizadas da animação.
