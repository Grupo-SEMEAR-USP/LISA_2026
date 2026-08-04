#include <Adafruit_INA219.h>
#include <Adafruit_PWMServoDriver.h>
#include <Wire.h>
#include "TCA9548.h"

TCA9548 mux(0x70);
Adafruit_INA219 ina219(0x40);
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

const float LIMITE_STALL_MA = 2500.0; // Corrente que define o stall 
bool sistemaEmLockout = false;        // Trava de emergência

TaskHandle_t TaskSensor;
SemaphoreHandle_t i2cMutex; // Protege o barramento I2C contra acessos simultâneos

#define SERVOMIN 150
#define SERVOMAX 600
uint8_t servo1 = 0;
uint8_t servo2 = 1;

void lerSensoresTask(void * pvParameters) {
  for(;;) {
    if(!sistemaEmLockout) {
      float corrente_S1 = 0;
      float corrente_S2 = 0;

      // Lê a corrente do Servo 1 com segurança
      if (xSemaphoreTake(i2cMutex, portMAX_DELAY)) {
        mux.selectChannel(0);
        corrente_S1 = ina219.getCurrent_mA();
        xSemaphoreGive(i2cMutex); // Libera o I2C
      }

      // Lê a corrente do Servo 2 com segurança
      if (xSemaphoreTake(i2cMutex, portMAX_DELAY)) {
        mux.selectChannel(1);
        corrente_S2 = ina219.getCurrent_mA();
        xSemaphoreGive(i2cMutex); // Libera o I2C
      }

      // Imprime no formato do Plotter 
      Serial.print("Corrente_S1:"); 
      Serial.print(corrente_S1); 
      Serial.print(","); 
      Serial.print("Corrente_S2:"); 
      Serial.println(corrente_S2);

      // FUSÍVEL:
      if (corrente_S1 > LIMITE_STALL_MA || corrente_S2 > LIMITE_STALL_MA) {
        Serial.println("STALL DETECTADO! Cortando motores.");
        
        sistemaEmLockout = true; // Trava o sistema
        
        // Pega o I2C para desligar os servos no PCA9685
        if (xSemaphoreTake(i2cMutex, portMAX_DELAY)) {
          mux.selectChannel(2);
          pwm.setPWM(servo1, 0, 4096); // 4096 = Sinal LOW total, desliga o PWM
          pwm.setPWM(servo2, 0, 4096);
          xSemaphoreGive(i2cMutex);
        }
      }
    }
    
    // Roda a ~50Hz (Intervalo de 20ms)
    vTaskDelay(pdMS_TO_TICKS(20)); 
  }
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("Iniciando o sistema...");

  Wire.begin(21, 22);
  
  // Cria o Mutex ANTES de começar a usá-lo
  i2cMutex = xSemaphoreCreateMutex();

  if (mux.begin() == false) {
    Serial.println("Erro: Não foi possível se comunicar com o TCA9548A.");
    while (1);
  }
  
  // Inicialização do hardware usando o Mutex por precaução

  xSemaphoreTake(i2cMutex, portMAX_DELAY);
  
  mux.selectChannel(0); 
  if (!ina219.begin()) {
    Serial.println("Erro no INA219 do Canal 0!");
    while (1);
  }
  
  mux.selectChannel(1); 
  if (!ina219.begin()) {
    Serial.println("Erro no INA219 do Canal 1!");
    while (1);
  }
  
  mux.selectChannel(2); 
  pwm.begin();
  pwm.setPWMFreq(50); 
  
  mux.disableAllChannels();
  xSemaphoreGive(i2cMutex); 
  
  // Fim da inicialização do hardware

  Serial.println("Tudo pronto! Armando Fusível Digital...");

  // Inicia a Tarefa de Monitoramento no Core 1, com Prioridade Alta
  xTaskCreatePinnedToCore(
    lerSensoresTask, 
    "Monitoramento_Stall", 
    4096, 
    NULL, 
    10, 
    &TaskSensor, 
    1
  );
}


// Função auxiliar para mapear graus (0-180) para pulsos do PCA9685 (150-600)
uint16_t grausParaPulsos(int graus) {
  // Limita os valores para evitar que um comando errado force fisicamente o servo
  if (graus < 0) graus = 0;
  if (graus > 180) graus = 180;
  
  return map(graus, 0, 180, SERVOMIN, SERVOMAX);
}

void loop() {
  // Verifica se o sistema está em emergência
  if (sistemaEmLockout) {
    // Para limpar o buffer caso a RASP continue mandando comando cega
    while (Serial.available() > 0) {
      Serial.read(); 
    }
    Serial.println("Sistema em emergência. Comandos ignorados.");
    delay(1000);
    return;
  }

  // Verifica se chegou algum comando da Raspberry Pi pela Serial
  if (Serial.available() > 0) {
    // Lê a linha até encontrar a quebra
    String comando = Serial.readStringUntil('\n');
    comando.trim();
    
    int idServo = -1;
    int angulo = -1;

    // Tenta extrair dois números inteiros da string no formato "ID ANGULO" (Ex: "1 180")
    if (sscanf(comando.c_str(), "%d %d", &idServo, &angulo) == 2) {
      
      // Converte de Graus para Pulsos PWM
      uint16_t pulso = grausParaPulsos(angulo);
      
      // Executa o movimento usando o Mutex para não bater com a leitura de corrente
      if (xSemaphoreTake(i2cMutex, portMAX_DELAY)) {
        mux.selectChannel(2); 
        pwm.setPWM(idServo, 0, pulso);
        xSemaphoreGive(i2cMutex); 
      }
      
      // Confirmação opcional para a RASP saber que o comando foi aceito
      // Serial.print("OK: Servo "); Serial.print(idServo); 
      // Serial.print(" movido para "); Serial.println(angulo);
      
    } else {
      Serial.println("Erro: Formato de comando invalido. Use 'ID ANGULO'");
    }
  }
}