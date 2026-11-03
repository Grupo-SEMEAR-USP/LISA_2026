# Guia de implementação de animações da LISA

**Objetivo:** orientar a criação e a integração de novas animações no firmware da LISA, sem exigir conhecimento de ROS 2 ou micro-ROS.

---

## 1. Visão geral

Na LISA, uma **animação** é uma sequência coordenada de ações realizadas por um ou mais componentes físicos. Por exemplo:

- `dancinha`: alternar posições de braços e cabeça em uma sequência;
- `acenar`: movimentar um braço repetidamente;
- `olhar_lados`: girar o pescoço para a esquerda e para a direita;
- `acender_led`: acender um LED durante um intervalo definido.

O firmware recebe uma solicitação de animação por meio da infraestrutura de comunicação já implementada. **A implementação de uma animação não precisa conhecer ROS, tópicos, serviços ou mensagens.** Ela deve apenas executar seu comportamento e utilizar as interfaces de hardware disponibilizadas pelo firmware.

A comunicação e a execução dos movimentos são responsabilidades separadas:

1. A camada de comunicação recebe uma solicitação.
2. O gerenciador de animações verifica se já existe uma animação em execução.
3. Se estiver livre, o gerenciador procura a animação solicitada em seu registro e tenta iniciá-la.
4. O `loop()` do firmware chama periodicamente a atualização do gerenciador.
5. O gerenciador atualiza exclusivamente a animação selecionada.
6. Quando a animação termina, o gerenciador libera a execução para a próxima solicitação.

Este documento explica como implementar uma animação e registrá-la no gerenciador.

### 1.1 Regra mais importante: animações não podem bloquear o firmware

O firmware precisa continuar executando seu `loop()` enquanto os componentes se movimentam. Isso permite que a placa atualize os motores, verifique o término da animação e continue atendendo às demais tarefas do firmware, inclusive à comunicação micro-ROS.

Por isso, não use esperas bloqueantes como:

```cpp
delay(1000);

while (motor_nao_chegou_na_posicao) {
    // Espera até o motor chegar.
}
```

Também evite laços `for` ou `while` que tentem executar toda a sequência de movimentos de uma vez.

Em vez disso, a animação deve avançar **um pequeno passo por chamada**, usando `millis()` para controlar o tempo. O `loop()` chama a função de atualização repetidamente, e ela decide se já chegou a hora de executar a próxima etapa.

---

## 2. Estrutura dos arquivos

Todos os arquivos-fonte `.cpp` do firmware devem ficar dentro da pasta especial `src/`. A Arduino IDE compila os arquivos dessa pasta e de suas subpastas, enquanto o arquivo `.ino` permanece na raiz do sketch.

A estrutura atual do firmware é:

```text
esp_lisa_micro_ros/
├── esp_lisa_micro_ros.ino
├── GUIA_IMPLEMENTACAO_ANIMACOES.md
└── src/
    ├── animacoes/
    │   ├── animacoes.h
    │   ├── animacoes.cpp
    │   ├── acender_led.h
    │   └── acender_led.cpp
    │
    └── hardware/
        ├── led.h
        └── led.cpp
```

Quando a interface de controle dos servos estiver definida, os arquivos correspondentes poderão ser adicionados em `src/hardware/`, por exemplo `motores.h` e `motores.cpp`. **Esses arquivos ainda não fazem parte da estrutura atual**; os exemplos que utilizam motores neste guia pressupõem uma interface ilustrativa que deverá ser combinada com a pessoa responsável pelo hardware.

### 2.1 Responsabilidade de cada arquivo

| Arquivo | Responsabilidade |
|---|---|
| `esp_lisa_micro_ros.ino` | Firmware principal. Cuida da comunicação micro-ROS, do `loop()` e chama a interface pública do gerenciador. |
| `src/animacoes/animacoes.h` | Declara somente as funções públicas do gerenciador de animações. |
| `src/animacoes/animacoes.cpp` | Mantém o registro das animações disponíveis e controla qual delas está em execução. |
| `src/animacoes/NOME.h` | Declara as quatro funções públicas de uma animação específica. |
| `src/animacoes/NOME.cpp` | Implementa somente o comportamento daquela animação. |
| `src/hardware/led.h` e `src/hardware/led.cpp` | Disponibilizam e implementam as operações de hardware do LED. |
| `src/hardware/motores.h` e `src/hardware/motores.cpp` | Futuramente, deverão disponibilizar e implementar a interface de controle dos servos. |

Cada animação deve ficar em seu próprio par de arquivos `.h` e `.cpp`. Dessa forma, uma pessoa pode desenvolver `acenar.cpp` sem misturar sua implementação com a de `dancinha.cpp` ou de outras animações.

### 2.2 Regras de organização e inclusão

Como o arquivo `.ino` está na raiz e os headers estão dentro de `src/`, os includes feitos diretamente no `.ino` usam o caminho a partir da raiz do sketch:

```cpp
#include "src/animacoes/animacoes.h"
#include "src/hardware/led.h"
```

Dentro de um arquivo `.cpp`, prefira incluir o header da própria animação pelo nome e os headers de outras pastas usando caminhos relativos. Por exemplo, em `src/animacoes/acender_led.cpp`:

```cpp
#include <Arduino.h>

#include "acender_led.h"
#include "../hardware/led.h"
```

Em `src/animacoes/animacoes.cpp`, os headers das animações que estão na mesma pasta também podem ser incluídos pelo nome:

```cpp
#include "animacoes.h"
#include "acender_led.h"
```

**Não coloque arquivos `.cpp` em pastas arbitrárias fora de `src/`.** Se isso acontecer, a Arduino IDE pode compilar o `.ino`, encontrar as declarações dos headers e, ainda assim, falhar na etapa de linkedição com erros `undefined reference`, porque as implementações não foram compiladas.

> **Importante:** os nomes e as funções reais de `src/hardware/motores.h` devem ser combinados com a pessoa responsável pelo hardware. Não presuma que essa interface já existe no repositório.

---

## 3. Interface que toda animação deve seguir

Para que o gerenciador consiga executar animações diferentes de maneira uniforme, cada animação deve oferecer quatro funções:

```cpp
void iniciar_NOME();
void atualizar_NOME();
void finalizar_NOME();
bool NOME_em_execucao();
```

Substitua `NOME` pelo nome da animação. Para a animação `acenar`, por exemplo:

```cpp
void iniciar_acenar();
void atualizar_acenar();
void finalizar_acenar();
bool acenar_em_execucao();
```

As declarações dessas funções devem ficar no header específico da animação, neste exemplo `src/animacoes/acenar.h`.

**Não adicione as declarações específicas de cada animação em `animacoes.h`.** Esse arquivo é reservado à interface genérica do gerenciador.

### 3.1 `iniciar_NOME()`

É chamada uma única vez quando a animação começa.

Deve:

- inicializar o estado interno da animação;
- definir qual é a primeira etapa;
- registrar o instante inicial com `millis()`;
- enviar os componentes para a primeira posição, se necessário.

Não deve conter esperas ou executar a sequência inteira.

### 3.2 `atualizar_NOME()`

É chamada repetidamente pelo gerenciador enquanto a animação está ativa.

Deve:

- verificar se já passou o tempo necessário para a próxima etapa;
- executar apenas a etapa que estiver pronta;
- atualizar o estado interno;
- marcar a animação como concluída quando chegar ao fim.

Essa função precisa ser rápida. Se ainda não chegou a hora de fazer algo, deve simplesmente retornar.

Quando a animação chegar ao fim normalmente, `atualizar_NOME()` deve deixar o hardware na condição final desejada e fazer `NOME_em_execucao()` retornar `false`. O gerenciador detecta esse retorno e libera a animação atual.

### 3.3 `finalizar_NOME()`

É chamada quando o firmware precisa interromper a animação antes de sua conclusão normal, por exemplo, durante uma desconexão do agente micro-ROS.

Deve:

- interromper a sequência;
- colocar os componentes em uma condição segura ou definida pelo projeto;
- limpar o estado interno;
- garantir que a animação seja considerada encerrada.

A posição final dos servos deve ser uma decisão consciente. Em alguns casos, faz sentido voltar à posição neutra; em outros, manter a última posição é desejável. Combine esse comportamento com a equipe.

**Atenção:** o gerenciador não chama `finalizar_NOME()` automaticamente quando uma animação termina normalmente. A própria rotina de atualização deve concluir o comportamento e sinalizar o término.

### 3.4 `NOME_em_execucao()`

Retorna:

- `true` enquanto a animação ainda estiver em andamento;
- `false` depois que ela terminar ou for finalizada.

O gerenciador usa essa informação para saber quando pode liberar a execução.

### 3.5 Interface do gerenciador

O arquivo `src/animacoes/animacoes.h` expõe quatro funções genéricas:

```cpp
bool iniciar_animacao(const char *nome);
bool atualizar_animacao();
void finalizar_animacao();
bool animacao_em_execucao();
```

A responsabilidade de cada uma é:

| Função | Comportamento |
|---|---|
| `iniciar_animacao(nome)` | Procura o nome no registro de animações e inicia a rotina correspondente. Retorna `true` se a animação iniciar com sucesso. |
| `atualizar_animacao()` | Atualiza a animação atualmente selecionada. Retorna `true` somente na chamada em que detecta que ela terminou. |
| `finalizar_animacao()` | Interrompe a animação atualmente selecionada, chama sua função de finalização e libera o gerenciador. |
| `animacao_em_execucao()` | Informa se existe uma animação selecionada/em execução. |

O gerenciador mantém um ponteiro para a animação atual e usa as funções registradas para chamar a implementação correta. Assim, o `.ino` não precisa conhecer individualmente `atualizar_acenar()`, `finalizar_acenar()` ou as funções das outras animações.

A comparação entre o nome recebido e os nomes registrados fica centralizada em `animacoes.cpp`. Portanto, não é necessário adicionar vários `strcmp()` ao callback ou ao `loop()` do firmware.

---

## 4. Como representar uma sequência de movimentos

Uma animação deve ser dividida em **etapas**. Cada etapa define:

1. quais componentes devem se movimentar;
2. para quais posições;
3. quanto tempo esperar antes de avançar para a próxima etapa.

Exemplo conceitual de uma animação:

| Etapa | Braço esquerdo | Braço direito | Pescoço | Duração da etapa |
|---|---:|---:|---:|---:|
| 1 | 40° | 140° | 90° | 700 ms |
| 2 | 90° | 90° | 60° | 500 ms |
| 3 | 140° | 40° | 120° | 700 ms |
| 4 | 90° | 90° | 90° | 500 ms |

Os valores são apenas ilustrativos. Os limites reais dependem da montagem mecânica e da calibração de cada servo.

A sequência pode ser representada por um `enum`:

```cpp
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

```cpp
static EtapaAcenar etapa_atual = CONCLUIDA;
```

O `static` mantém o valor entre chamadas de `atualizar_acenar()`. Sem isso, a variável seria recriada a cada chamada e a animação perderia seu progresso.

---

## 5. Exemplo completo: animação `acenar`

Este exemplo demonstra a estrutura. Ele pressupõe que exista uma interface de hardware semelhante a:

```cpp
// Exemplo ilustrativo de src/hardware/motores.h
void mover_servo(int id_servo, int angulo);
```

A implementação real dessa função é responsabilidade da camada de hardware. Ela deve enviar o comando ao servo sem introduzir esperas bloqueantes.

### 5.1 Arquivo `src/animacoes/acenar.cpp`

```cpp
#include <Arduino.h>

#include "acenar.h"
#include "../hardware/motores.h"

// Identificador ilustrativo do servo do braço direito.
// Use os identificadores definidos em src/hardware/motores.h.
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

### 5.2 Arquivo `src/animacoes/acenar.h`

Crie um header próprio para a animação:

```cpp
#ifndef ACENAR_H
#define ACENAR_H

void iniciar_acenar();
void atualizar_acenar();
void finalizar_acenar();
bool acenar_em_execucao();

#endif
```

### 5.3 Registrar a animação em `src/animacoes/animacoes.cpp`

Para que o gerenciador reconheça a animação, inclua o header dela no arquivo do gerenciador:

```cpp
#include "acenar.h"
```

Depois, adicione uma entrada ao array `animacoes`, mantendo as animações que já estavam registradas. Cada entrada segue a ordem: nome recebido, função de início, função de atualização, função de finalização e função que consulta o estado.

Exemplo de como o registro pode ficar depois de adicionar `acenar`:

```cpp
static const Animacao animacoes[] = {
    {
        "acender_led",
        iniciar_acender_led,
        atualizar_acender_led,
        finalizar_acender_led,
        acender_led_em_execucao
    },
    {
        "acenar",
        iniciar_acenar,
        atualizar_acenar,
        finalizar_acenar,
        acenar_em_execucao
    }
};
```

O nome `"acenar"` deve ser exatamente o nome usado por quem solicita a animação pelo protocolo de comunicação. A partir desse registro, o gerenciador consegue iniciar, atualizar e finalizar a animação sem qualquer alteração no callback ou no `loop()` do `.ino`.

> **Não altere `src/animacoes/animacoes.h` para cadastrar uma animação.** Esse header contém apenas as funções genéricas do gerenciador. As funções específicas ficam no header da própria animação, e o cadastro é feito no array de `animacoes.cpp`.

### 5.4 O que acontece durante a execução?

1. `iniciar_acenar()` posiciona o braço e registra o horário inicial.
2. O `loop()` chama `atualizar_animacao()`, que encaminha a chamada para `atualizar_acenar()`.
3. Antes de completar 400 ms, a função retorna imediatamente.
4. Depois de 400 ms, a função envia o próximo comando e avança uma etapa.
5. Esse processo se repete até a etapa `CONCLUIDA`.
6. `acenar_em_execucao()` passa a retornar `false`.
7. O gerenciador detecta o término, limpa a animação atual e fica disponível para outra solicitação.

Observe que o exemplo não espera o servo chegar fisicamente à posição. Ele envia um comando e avança após o intervalo definido. Se o projeto precisar confirmar a posição real, será necessário implementar leitura/feedback do servo ou ajustar os tempos de acordo com os testes mecânicos.

---

## 6. Movimentando vários servos na mesma etapa

Uma etapa pode comandar vários servos. Basta enviar os comandos na mesma chamada de atualização:

```cpp
case POSICAO_INICIAL:
    mover_servo(SERVO_BRACO_ESQUERDO, 40);
    mover_servo(SERVO_BRACO_DIREITO, 140);
    mover_servo(SERVO_PESCOCO, 90);

    etapa_atual = PROXIMA_ETAPA;
    break;
```

Isso inicia os comandos praticamente no mesmo instante. A movimentação física simultânea depende de como a camada de hardware controla os servos.

**Não** faça isto:

```cpp
mover_servo(SERVO_BRACO_ESQUERDO, 40);
delay(500);
mover_servo(SERVO_BRACO_DIREITO, 140);
```

Esse padrão bloqueia o firmware e ainda faz os movimentos começarem em momentos diferentes.

---

## 7. Movimento gradual: posição-alvo e interpolação

Enviar um ângulo ao servo normalmente define uma **posição-alvo**. Dependendo da biblioteca e do hardware, o servo pode tentar chegar até ela na velocidade própria do motor.

Se for necessário controlar a velocidade, pode-se implementar movimento gradual: em vez de saltar diretamente de 90° para 150°, aumentar o ângulo aos poucos.

Exemplo conceitual:

```cpp
angulo_atual += 1;
mover_servo(SERVO_BRACO_DIREITO, angulo_atual);
```

Esse incremento deve ocorrer somente quando chegar o instante da próxima atualização, também controlado com `millis()`.

Uma alternativa é interpolar entre posição inicial e final durante uma duração definida:

\[
angulo(t) = angulo_{inicial} + \frac{t}{T}(angulo_{final} - angulo_{inicial})
\]

em que `t` é o tempo decorrido e `T` é a duração total do movimento. Ao atingir `T`, o ângulo deve ser exatamente o alvo.

Para uma animação com vários servos, cada servo pode ter seu próprio ângulo inicial e final, mas compartilhar o mesmo tempo de movimento. Isso permite que braços e pescoço se movimentem de forma coordenada.

A interpolação deve respeitar os limites mecânicos e os limites configurados para cada servo. Não assuma que todo servo pode operar com segurança entre 0° e 180°.

---

## 8. Repetições e animações em loop

Algumas animações precisam repetir um movimento algumas vezes. Há duas maneiras comuns:

### Repetição com contador

```cpp
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

```cpp
repeticoes = 0;
```

### Repetição contínua

Se a animação precisar continuar até ser interrompida, não marque `CONCLUIDA` ao final do ciclo. Volte para a primeira etapa.

Nesse caso, `NOME_em_execucao()` continuará retornando `true` até que `finalizar_NOME()` seja chamada.

Combine previamente se uma animação é finita ou contínua. Animações contínuas precisam ter uma forma clara de interrupção.

---

## 9. Regras de segurança e boas práticas

Antes de entregar uma animação, confira os seguintes pontos:

### Movimento e limites

- [ ] Todos os ângulos estão dentro dos limites mecânicos do robô.
- [ ] Os movimentos não forçam braços, articulações, cabos ou estruturas.
- [ ] As posições iniciais e finais foram testadas com cuidado.
- [ ] A animação não presume que todos os servos têm a mesma orientação ou calibração.
- [ ] Movimentos simultâneos não causam colisões entre peças.

### Execução não bloqueante

- [ ] Não existe `delay()` na animação.
- [ ] Não existem laços `while` esperando motor ou tempo.
- [ ] Cada chamada de `atualizar_NOME()` executa rapidamente e retorna.
- [ ] O tempo é controlado com `millis()` ou mecanismo não bloqueante equivalente.
- [ ] A animação não executa toda a sequência dentro de `iniciar_NOME()`.

### Estado e encerramento

- [ ] O estado inicial é configurado em `iniciar_NOME()`.
- [ ] `NOME_em_execucao()` retorna `true` durante toda a execução.
- [ ] Ao terminar normalmente, a animação passa a retornar `false`.
- [ ] `finalizar_NOME()` interrompe a sequência e deixa os componentes em uma condição definida.
- [ ] Contadores, temporizadores e variáveis de estado são reinicializados ao iniciar novamente.
- [ ] O comportamento de término normal está implementado em `atualizar_NOME()`, sem depender de uma chamada automática a `finalizar_NOME()`.

### Organização e integração

- [ ] Os arquivos `.h` e `.cpp` da animação estão em `src/animacoes/`.
- [ ] As quatro funções específicas estão declaradas no header da própria animação (`NOME.h`).
- [ ] A animação foi incluída e registrada no array de `src/animacoes/animacoes.cpp`.
- [ ] `src/animacoes/animacoes.h` contém somente a interface pública do gerenciador.
- [ ] O código usa a interface de `src/hardware/`, em vez de duplicar o controle dos componentes.
- [ ] A animação não contém código de ROS 2 ou micro-ROS.
- [ ] Todos os arquivos `.cpp` estão dentro de `src/` para serem compilados pela Arduino IDE.
- [ ] Os nomes das funções seguem o padrão definido neste guia.

---

## 10. Erros comuns

| Problema | Causa provável | Como corrigir |
|---|---|---|
| O micro-ROS para de responder durante a animação | Uso de `delay()` ou laço de espera | Transformar a rotina em etapas não bloqueantes. |
| A animação sempre volta para a primeira etapa | Variável de estado local comum, recriada a cada chamada | Usar variável `static` ou estado persistente da animação. |
| A animação nunca termina | Estado final não é alcançado ou a função de consulta está incorreta | Verificar as transições e retornar `false` no estado final. |
| A animação não reinicia corretamente | Temporizadores ou contadores não são reinicializados | Reinicializar todo o estado em `iniciar_NOME()`. |
| Os movimentos ficam fora de sincronia | Cada servo é comandado em momentos diferentes ou há esperas bloqueantes | Enviar os comandos da mesma etapa juntos e controlar o tempo centralmente. |
| O servo se move de forma brusca | Salto grande entre posições-alvo | Usar interpolação ou limitar a velocidade do movimento. |
| O mecanismo força ou bate no fim de curso | Ângulo fora da faixa mecânica ou calibração incorreta | Reduzir os limites e testar cada articulação com cuidado. |
| Erro `undefined reference` durante a linkedição | Arquivo `.cpp` fora de `src/`, arquivo não compilado ou assinatura divergente | Conferir a localização do `.cpp` e comparar as assinaturas entre header e implementação. |
| O gerenciador não reconhece uma animação | Header não incluído ou entrada ausente no array de `animacoes.cpp` | Incluir o header da animação e cadastrá-la no array. |

---

## 11. Como criar uma nova animação: passo a passo

Para implementar, por exemplo, uma animação chamada `dancinha`:

1. **Defina a sequência:** descreva em uma tabela as etapas, os componentes envolvidos, as posições e os intervalos.
2. **Confira o hardware disponível:** consulte os headers em `src/hardware/` para saber quais operações já existem. Se a interface de motores ainda não estiver disponível, combine sua criação com a pessoa responsável pelo hardware.
3. **Crie `src/animacoes/dancinha.h`:** declare `iniciar_dancinha()`, `atualizar_dancinha()`, `finalizar_dancinha()` e `dancinha_em_execucao()`.
4. **Crie `src/animacoes/dancinha.cpp`:** implemente as quatro funções. Inclua `dancinha.h` e os headers de hardware necessários.
5. **Implemente por etapas:** use uma variável de estado e `millis()`; não use esperas bloqueantes.
6. **Registre a animação:** inclua `dancinha.h` em `src/animacoes/animacoes.cpp` e adicione uma entrada ao array `animacoes`.
7. **Não altere o `.ino` para cadastrar a animação:** o `.ino` já conversa com o gerenciador por meio de `iniciar_animacao()`, `atualizar_animacao()`, `finalizar_animacao()` e `animacao_em_execucao()`.
8. **Teste os limites:** inicialmente, teste com movimentos pequenos e sem pessoas próximas às partes móveis.
9. **Teste o término:** confirme que `dancinha_em_execucao()` retorna `false` no final e que o gerenciador libera a animação.
10. **Teste a interrupção:** confirme que `finalizar_dancinha()` interrompe a sequência de forma segura quando o firmware chama `finalizar_animacao()`.

### 11.1 Modelo para copiar

Use este esqueleto para criar os dois arquivos de uma nova animação. Substitua `NOME` pelo nome escolhido e implemente as etapas.

**Arquivo `src/animacoes/NOME.h`:**

```cpp
#ifndef NOME_H
#define NOME_H

void iniciar_NOME();
void atualizar_NOME();
void finalizar_NOME();
bool NOME_em_execucao();

#endif
```

**Arquivo `src/animacoes/NOME.cpp`:**

```cpp
#include <Arduino.h>

#include "NOME.h"
#include "../hardware/motores.h"  // Se a animação utilizar os motores.

// Estados possíveis da animação.
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

    // Configure a posição inicial dos componentes.
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
            // Comande um ou mais componentes.
            etapa_atual = ETAPA_2;
            break;

        case ETAPA_2:
            // Comande o próximo movimento.
            etapa_atual = ETAPA_3;
            break;

        case ETAPA_3:
            // Último movimento. Deixe os componentes na posição final desejada.
            etapa_atual = CONCLUIDA;
            break;

        case CONCLUIDA:
            break;
    }
}

void finalizar_NOME() {
    // Interrompa a sequência e deixe os componentes em condição segura.
    etapa_atual = CONCLUIDA;
}

bool NOME_em_execucao() {
    return etapa_atual != CONCLUIDA;
}
```

No esqueleto, substitua `NOME` pelo mesmo identificador em todos os lugares. Por exemplo, para `dancinha`, use `EtapaDancinha`, `iniciar_dancinha()`, `atualizar_dancinha()`, `finalizar_dancinha()` e `dancinha_em_execucao()`.

### 11.2 Cadastro em `src/animacoes/animacoes.cpp`

1. Adicione `#include "dancinha.h"` junto aos outros headers de animações.
2. Acrescente uma entrada ao array `animacoes`:

```cpp
{
    "dancinha",
    iniciar_dancinha,
    atualizar_dancinha,
    finalizar_dancinha,
    dancinha_em_execucao
}
```

Não substitua as entradas existentes: apenas acrescente a nova entrada, separando os elementos por vírgula.

### 11.3 Compilação pela Arduino IDE

Antes de compilar, confira:

- o arquivo `.ino` continua diretamente dentro da pasta `esp_lisa_micro_ros/`;
- todos os arquivos `.cpp` estão dentro de `esp_lisa_micro_ros/src/` ou de suas subpastas;
- os headers estão nos caminhos indicados nos exemplos;
- o novo header foi incluído em `animacoes.cpp`;
- a animação foi adicionada ao array de registro.

Se o `.ino` não encontrar um header, confira o caminho do `#include`. Se a compilação chegar à linkedição e apresentar `undefined reference`, confira se o `.cpp` correspondente está dentro de `src/` e se os nomes e assinaturas das funções coincidem entre `.h` e `.cpp`.

---

## 12. O que a pessoa responsável pela animação precisa entregar

Para cada nova animação, entregue:

1. O arquivo `src/animacoes/NOME.h`, com as quatro declarações públicas.
2. O arquivo `src/animacoes/NOME.cpp`, com a implementação da animação.
3. O cadastro da animação em `src/animacoes/animacoes.cpp` (novo include e nova entrada no array).
4. Uma breve descrição da sequência de movimentos, incluindo os componentes utilizados, posições e tempos.
5. A confirmação de que a animação não usa esperas bloqueantes.
6. O resultado dos testes de início, execução, término normal e interrupção.

**Resumo:** a pessoa que implementa uma animação não precisa conhecer ROS 2 nem alterar a comunicação da ESP32. Ela precisa conhecer a interface de hardware disponível, implementar uma sequência de etapas não bloqueantes, seguir as quatro funções padronizadas, criar um header próprio e registrar a animação no gerenciador.