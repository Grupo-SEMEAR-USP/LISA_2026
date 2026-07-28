// Incluindo as Bibliotecas: 
#include <ESP32Servo.h>

// Cria o objeto para controlar o servo:
Servo meuServo;

// Define o pino onde o fio de sinal está ligado. Evite usar pinos que são INPUT ONLY (como 34, 35, 36, 39)! 
int pinoServo = 13; 

void setup() {
  Serial.begin(115200);
  meuServo.attach(pinoServo);
  Serial.println("Iniciando teste do Servo Motor...");
}

void loop() {
  // --- Mover de 0 a 180 graus ---
  Serial.println("Indo para 180 graus...");
  for (int pos = 0; pos <= 180; pos += 1) { 
    meuServo.write(pos); // Manda o servo para a posição 'pos'
    delay(15);           
  }
  delay(1000); // Espera 1 segundo na ponta
  // --- Mover de 180 a 0 graus ---
  Serial.println("Voltando para 0 graus...");
  for (int pos = 180; pos >= 0; pos -= 1) { 
    meuServo.write(pos); 
    delay(15); 
  }

  delay(1000); // Espera 1 segundo na outra ponta
}
