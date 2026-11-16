#ifndef MOTORES_H
#define MOTORES_H

// Identificadores dos servos disponíveis.
enum ServoId {
    SERVO_1,
    SERVO_2
};

// Inicializa os servos e posiciona ambos em 90 graus.
void motores_inicializar();

// Envia um comando de posição para o servo selecionado.
void mover_servo(ServoId servo, int angulo);

#endif