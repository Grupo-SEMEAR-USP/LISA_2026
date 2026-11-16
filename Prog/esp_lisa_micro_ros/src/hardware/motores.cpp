#include <Arduino.h>
#include <ESP32Servo.h>

#include "motores.h"

// ============================================================
// CONFIGURACOES DOS SERVOS
// ============================================================

#define SERVO_1_PIN 18
#define SERVO_2_PIN 19

// Objetos responsáveis pelo controle dos servos.
static Servo servo1;
static Servo servo2;


// ============================================================
// INICIALIZACAO
// ============================================================

void motores_inicializar() {

    // Inicializa os servos nos GPIOs definidos.
    servo1.attach(SERVO_1_PIN);
    servo2.attach(SERVO_2_PIN);

    // Posiciona ambos os servos na posição neutra.
    servo1.write(90);
    servo2.write(90);
}


// ============================================================
// MOVIMENTACAO
// ============================================================

void mover_servo(ServoId servo, int angulo) {

    // Limita o ângulo à faixa de 0 a 180 graus.
    if (angulo < 0) {
        angulo = 0;
    }

    if (angulo > 180) {
        angulo = 180;
    }

    // Envia o comando para o servo selecionado.
    switch (servo) {

        case SERVO_1:
            servo1.write(angulo);
            break;

        case SERVO_2:
            servo2.write(angulo);
            break;
    }
}