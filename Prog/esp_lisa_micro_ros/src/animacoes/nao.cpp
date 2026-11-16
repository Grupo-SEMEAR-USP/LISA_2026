#include <Arduino.h>

#include "nao.h"
#include "../hardware/motores.h"

// ============================================================
// CONFIGURACOES
// ============================================================

static const int ANGULO_MINIMO = 60;
static const int ANGULO_MAXIMO = 120;

static const unsigned long INTERVALO_MOVIMENTO_MS = 15;


// ============================================================
// ESTADOS DA ANIMACAO
// ============================================================

enum EtapaNao {
    SUBINDO,
    DESCENDO,
    CONCLUIDA
};

// Estado atual da animação.
static EtapaNao etapa_atual = CONCLUIDA;

// Ângulo atual do primeiro servo.
static int angulo_atual = ANGULO_MINIMO;

// Instante da última atualização.
static unsigned long instante_movimento = 0;


// ============================================================
// INICIAR ANIMACAO
// ============================================================

void iniciar_nao() {

    etapa_atual = SUBINDO;

    angulo_atual = ANGULO_MINIMO;

    instante_movimento = millis();

    // Posiciona os servos em sentidos opostos.
    mover_servo(SERVO_1, angulo_atual);
    mover_servo(SERVO_2, 180 - angulo_atual);
}


// ============================================================
// ATUALIZAR ANIMACAO
// ============================================================

void atualizar_nao() {

    // Não há nada para atualizar se a animação terminou.
    if (etapa_atual == CONCLUIDA) {
        return;
    }

    // Aguarda o intervalo entre os movimentos sem bloquear.
    if (millis() - instante_movimento < INTERVALO_MOVIMENTO_MS) {
        return;
    }

    instante_movimento = millis();

    // --------------------------------------------------------
    // Movimento de subida: 60 -> 120 graus
    // --------------------------------------------------------

    if (etapa_atual == SUBINDO) {

        angulo_atual++;

        if (angulo_atual >= ANGULO_MAXIMO) {
            etapa_atual = DESCENDO;
        }
    }

    // --------------------------------------------------------
    // Movimento de descida: 120 -> 60 graus
    // --------------------------------------------------------

    else if (etapa_atual == DESCENDO) {

        angulo_atual--;

        if (angulo_atual <= ANGULO_MINIMO) {
            etapa_atual = CONCLUIDA;
        }
    }

    // Primeiro servo acompanha o ângulo atual.
    mover_servo(SERVO_1, angulo_atual);

    // Segundo servo realiza o movimento inverso.
    mover_servo(SERVO_2, 180 - angulo_atual);
}


// ============================================================
// FINALIZAR ANIMACAO
// ============================================================

void finalizar_nao() {

    // Interrompe a animação e retorna à posição neutra.
    mover_servo(SERVO_1, 90);
    mover_servo(SERVO_2, 90);

    etapa_atual = CONCLUIDA;
}


// ============================================================
// VERIFICAR ESTADO
// ============================================================

bool nao_em_execucao() {
    return etapa_atual != CONCLUIDA;
}