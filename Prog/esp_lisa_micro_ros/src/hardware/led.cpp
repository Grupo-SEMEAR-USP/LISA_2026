#include <Arduino.h>
#include "led.h"

#define LED_PIN 4


// ------------------------------------------------------------
// Inicializa o LED
// ------------------------------------------------------------

void led_inicializar() {
    pinMode(LED_PIN, OUTPUT);
    led_desligar();
}


// ------------------------------------------------------------
// Liga o LED
// ------------------------------------------------------------

void led_ligar() {
    digitalWrite(LED_PIN, HIGH);
}


// ------------------------------------------------------------
// Desliga o LED
// ------------------------------------------------------------

void led_desligar() {
    digitalWrite(LED_PIN, LOW);
}