#include <Stepper.h> // importa as bibliotecas 

const int passosPorVolta = 2048;

// Usando a ordem IN1, IN2, IN3 e IN4 -- USEI O ARDUINO, TEM QUE VERIFICAR SE OS MESMOS PINOS FUNCIONAMMMM!!!! =) 
Stepper motor(passosPorVolta,8,10,9,11);

// -- Definindo Funções Auxiliares --

int grausParaPassos(float angulo) {
  return round((angulo / 360.0) * passosPorVolta);
}
/*
Essa função realiza a conversão de graus para passos
*/

void moverSuave(int quantidadePassos, int atrasoMs) {
  int sentido;
  if (quantidadePassos >= 0) {
    sentido = 1;
  }
  else {
    sentido = -1;
    quantidadePassos = -quantidadePassos;
  }
  for (int i = 0; i < quantidadePassos; i++) {
    motor.step(sentido);
    delay(atrasoMs);
  }
}
/*
Essa função realiza o movimento "suave" para o motor (não deixa que ele realize conversões bruscas, gerando picos de corrente) 
*/

void movimentoSimSuave(int repeticoes, float angulo) {

  int passos = grausParaPassos(angulo);
  for (int i = 0; i < repeticoes; i++) {
    moverSuave(passos, 2); // Desce a cabeça
    delay(150);
    moverSuave(-2 * passos, 2); // Sobe passando pelo centro
    delay(150);
    moverSuave(passos, 2); // Volta para o centro
    delay(300);
  }
}
/*
Função que realiza o movimento do "SIM". Ela utilzia a função moverSuave como auxiliar 
*/

// -- Main -- 

void setup() {
  motor.setSpeed(10); // Velocidade máxima do Stepper
}

void loop() {
  movimentoSimSuave(3, 20); // Faz três movimentos de "sim"
  delay(3000);
}
