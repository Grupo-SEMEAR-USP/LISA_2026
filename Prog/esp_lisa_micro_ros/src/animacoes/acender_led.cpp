#include <Arduino.h>

#include "acender_led.h"
#include "../hardware/led.h"

static const unsigned long DURACAO_ANIMACAO_MS = 5000;

static bool em_execucao = false;
static unsigned long instante_inicio = 0;

void iniciar_acender_led() {
    em_execucao = true;
    instante_inicio = millis();

    led_ligar();
}

void atualizar_acender_led() {
    if (!em_execucao) {
        return;
    }

    if (millis() - instante_inicio >= DURACAO_ANIMACAO_MS) {
        led_desligar();
        em_execucao = false;
    }
}

void finalizar_acender_led() {
    led_desligar();
    em_execucao = false;
}

bool acender_led_em_execucao() {
    return em_execucao;
}