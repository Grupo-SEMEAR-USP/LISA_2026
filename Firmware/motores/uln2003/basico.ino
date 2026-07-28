#include <Stepper.h> // importa a biblioteca do stepper 

// Aproximadamente 2048 passos por volta no modo de passo completo
const int passosPorVolta = 2048; 

// IN1, IN3, IN2, IN4 - a ordem dos pinos é importante se não dá ruim =) 
Stepper motor(passosPorVolta,8,10,9,11); // mudar os pinos. fiz usando arduino =) 

void setup() {
  motor.setSpeed(10);  // Velocidade em rotações por minuto
}

void loop() {
  motor.step(passosPorVolta);   // Uma volta no sentido horário
  delay(1000);
  motor.step(-passosPorVolta);  // Uma volta no sentido anti-horário
  delay(1000);
}
