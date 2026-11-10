//
// Código do modo feliz da LISA 
//

// Considerando a seguinte sequência de pinos do PCA 9685 

#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
#include <math.h>

// Inicialização do PCA9685
Adafruit_PWMServoDriver pca = Adafruit_PWMServoDriver(0x40);

// Pinos de comunicação I2C do ESP32
#define SDA_PIN 21
#define SCL_PIN 22

// Canais dos servomotores no PCA9685
#define ORELHA_DIREITA  0
#define ORELHA_ESQUERDA 1
#define BRACO_DIREITO   2
#define BRACO_ESQUERDO  3
#define PESCOCO_1       4
#define PESCOCO_2       5
#define BASE            6

// Configurações dos servomotores
#define FREQUENCIA_PWM 50
#define SERVO_MIN_US 1000
#define SERVO_MAX_US 2000

// Converte um ângulo para o pulso PWM correspondente
void moverServo(uint8_t canal, int angulo) {
  angulo = constrain(angulo, 0, 180);

  int pulso = map(angulo, 0, 180, SERVO_MIN_US, SERVO_MAX_US);
  pca.writeMicroseconds(canal, pulso);
}

// Inicializa todos os servomotores na posição neutra
void posicaoInicial() {
  moverServo(ORELHA_DIREITA, 90);
  moverServo(ORELHA_ESQUERDA, 90);
  moverServo(BRACO_DIREITO, 90);
  moverServo(BRACO_ESQUERDO, 90);
  moverServo(PESCOCO_1, 90);
  moverServo(PESCOCO_2, 90);
  moverServo(BASE, 90);
}



// Retorna suavemente o pescoço à posição neutra
void centralizarPescoco() {
  for (int angulo = 60; angulo <= 90; angulo++) {
    moverServo(PESCOCO_1, angulo);
    moverServo(PESCOCO_2, angulo);
    delay(15);
  }
}
#include <math.h>

// Definição da Função - LISA feliz
void feliz() {
  const int ciclos = 4;
  const int passos = 100;
  const int tempoPasso = 20;

  // Amplitudes iniciais, ajustar após calibração
  const float ampOrelha = 15;
  const float ampBraco = 20;
  const float ampBase = 10;

  for (int ciclo = 0; ciclo < ciclos; ciclo++) {
    for (int i = 0; i <= passos; i++) {
      float fase = 2.0 * PI * i / passos;
      float movimento = sin(fase);

      // Orelhas alternadas
      moverServo(ORELHA_DIREITA, 90 + ampOrelha * movimento);
      moverServo(ORELHA_ESQUERDA, 90 - ampOrelha * movimento);

      // Braços alternados
      moverServo(BRACO_DIREITO, 90 + ampBraco * movimento);
      moverServo(BRACO_ESQUERDO, 90 - ampBraco * movimento);

      // Base: movimento de vai e vem
      moverServo(BASE, 90 + ampBase * movimento);
      delay(tempoPasso);
    }
  }

  // Posição neutra dos servos envolvidos
  moverServo(ORELHA_DIREITA, 90);
  moverServo(ORELHA_ESQUERDA, 90);
  moverServo(BRACO_DIREITO, 90);
  moverServo(BRACO_ESQUERDO, 90);
  moverServo(BASE, 90);
}
void setup() {
  Serial.begin(115200);
  // Inicializa o barramento I2C
  Wire.begin(SDA_PIN, SCL_PIN);
  // Inicializa o PCA9685
  if (!pca.begin()) {
    Serial.println("Erro: PCA9685 nao encontrado!");
    while (true) {
      delay(1000);
    }
  }
  pca.setPWMFreq(FREQUENCIA_PWM);
  delay(10);
  Serial.println("Sistema LISA inicializado!");
  posicaoInicial();
  delay(1000);
}

void loop() {
}
