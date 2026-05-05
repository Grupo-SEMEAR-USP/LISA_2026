#include <ESP32Servo.h>
#include "stdio.h"

// SERVOS
// Pinos 
#define basePin               18
#define bracoDireitoPin       19
#define bracoEsquerdoPin      21
#define cabecaVerticalPin     22  
#define cabecaHorizontalPin   23
#define orelhaDireitaPin      33
#define orelhaEsquerdaPin     12

// Indices no vetor de servo 
#define base                   0 
#define bracoDireito           1
#define bracoEsquerdo          2
#define cabecaVertical         3
#define cabecaHorizontal       4
#define orelhaDireita          5
#define orelhaEsquerda         6
 

// CONSTANTES GERAIS 
#define ESQUERDA 0
#define DIREITA 1 

// VARIAVEIS PARA REGULAR OS SERVOS
Servo servo[7]; 
// ANGULOS DE ESPERA DOS SERVOMOTORES 
#define posPadraoBase                90               
#define posPadraoBracoDireito         0                
#define posPadraoBracoEsquerdo        0
#define posPadraoCabecaVertical       0             
#define posPadraoCabecaHorizontal    90            
#define posPadraoOrelhaDireita       90
#define posPadraoOrelhaEsquerda      90
// Essas posicoes sao as que os servos devem ser colocados quando forem ser inseridos no robo. Uma vez que e utilizada como posicao 0 (padrao) dos servos. 
// Posicoes maximas e minimas: 
#define angIdaBraco 135
#define angVoltaBraco 45
#define angSimCabeca 60
#define angIdaNaoCabeca 150
#define angVoltaNaoCabeca 30
#define angIdaBase 150
#define angVoltaBase 30
#define bracoLevantado 180
#define MovEnable 1       /* Define se pode ocorrer o movimento */

// ESTADOS A SEREM ATUALIZADOS:
volatile bool andando = false;
int posBase;  
int posBracoDireito; 
int posBracoEsquerdo;
int posCabecaVertical; 
int posCabecaHorizontal;
int posOrelhaDireita;
int posOrelhaEsquerda;
int print = 1;                // Variavel que indica se printa ou nao no monitor serial (Tomar cuidado para nao haver requisicoes do monitor serial ao mesmo tempo)    
/*
Logica para andando: 
- Quando ja estiver andando e for dado o comando de andar, nao reseta o andar. 
- Impede que ande quando a distancia entre obstaculo for menor que a distancia minima realize o andar (poderia ser so um AND dentro de um if, por isso talvez nem seja necessario)
*/

// TASK HANDLE
TaskHandle_t Task1;
TaskHandle_t Task2;

void setup()
{   
  Serial.begin(9600); 
  // Inicializa componentes
  servo[base].attach(basePin);
  servo[bracoDireito].attach(bracoDireitoPin);
  servo[bracoEsquerdo].attach(bracoEsquerdoPin);
  servo[cabecaVertical].attach(cabecaVerticalPin);
  servo[cabecaHorizontal].attach(cabecaHorizontalPin);
  servo[orelhaDireita].attach(orelhaDireitaPin);
  servo[orelhaEsquerda].attach(orelhaEsquerdaPin);

  // Inicializa as task para utilizar o DualCore 
  // Create a task that will be executed in the Task1code() function, with priority 1 and executed on core 0
  xTaskCreatePinnedToCore(Task1code, "Task1", 8192, NULL, 2, &Task1, 0);                           
  delay(500); 

  // Create a task that will be executed in the Task2code() function, with priority 1 and executed on core 1
  xTaskCreatePinnedToCore(Task2code, "Task2", 8192, NULL, 1, &Task2, 1);          
  delay(500); 
  
  setPosicaoPadrao(); 
}

void Task1code( void * pvParameters ){
  while(true){
  int tempo = 50; 

  vTaskDelay(100);
  vTaskDelay(tempo / portTICK_PERIOD_MS);   // Suspender a task por um intervalo de tempo para 
  /* Isso permite que o EspWatchdog retorne o controle para a Esp32 */
  }
}

//Task2code: Controla o andar do robô
/* Proposta de solucao: Separar o processamento dos servos maiores do dos servos menores */
void Task2code( void * pvParameters ) {
  while(true){
  int tempo = 50;
  //UmSwing();
  //oscilaLados(1); 
  //DaUmPassoFrente();
  //DaUmPassoTras(); 
  vTaskDelay(tempo / portTICK_PERIOD_MS);
  }
}
//  setPosicaoPadrao(); 


void loop(){}


// --------------------------------------------------- ################# FUNCOES DO SERVOMOTOR: #################### ----------------------------------------------------------------
// Coloca os servos nas posicoes padroes 
void setPosicaoPadrao(){
  int tempo = 100; 
  posBase = posPadraoBase;  
  posBracoDireito = posPadraoBracoDireito; 
  posBracoEsquerdo = posPadraoBracoEsquerdo;
  posCabecaVertical = posPadraoCabecaVertical; 
  posCabecaHorizontal = posPadraoCabecaHorizontal;
  posOrelhaDireita = posPadraoOrelhaDireita;
  posOrelhaEsquerda = posPadraoOrelhaEsquerda;
  
  if(print) {
    Serial.print("Setando posicao no servo Base...");
    Serial.println(posPadraoBase); 
  }
  servo[base].write(posPadraoBase);
  vTaskDelay(tempo);

  if(print) {
    Serial.print("Setando posicao no servo Braco Direito..."); 
    Serial.println(posPadraoBracoDireito);
  }
  servo[bracoDireito].write(posPadraoBracoDireito);
  vTaskDelay(tempo);

  if(print) {
    Serial.print("Setando posicao no servo Braco Esquerdo..."); 
    Serial.println(posPadraoBracoEsquerdo); 
  }
  servo[bracoEsquerdo].write(posPadraoBracoEsquerdo);
  vTaskDelay(tempo);

  if(print) {
    Serial.print("Setando posicao no servo Cabeca Vertical...");  
    Serial.println(posPadraoCabecaVertical); 
  }
  servo[cabecaVertical].write(posPadraoCabecaVertical);
  vTaskDelay(tempo / portTICK_PERIOD_MS);

  if(print) {
    Serial.print("Setando posicao no servo Cabeca Horizontal..."); 
    Serial.println(posPadraoCabecaHorizontal);
  }
  servo[cabecaHorizontal].write(posPadraoCabecaHorizontal);
  vTaskDelay(tempo / portTICK_PERIOD_MS);

  if(print) { 
    Serial.print("Setando posicao no servo Orelha Direita...");  
    Serial.println(posPadraoOrelhaDireita);  
  }
  servo[orelhaDireita].write(posPadraoOrelhaDireita); 
  vTaskDelay(tempo / portTICK_PERIOD_MS);

  if(print) { 
    Serial.print("Setando posicao no servo Orelha Esquerda...");  
    Serial.println(posPadraoOrelhaEsquerda);  
  }
  servo[orelhaEsquerda].write(posPadraoOrelhaEsquerda); 
  vTaskDelay(tempo / portTICK_PERIOD_MS);
}

// Seta os servos para 90 -> Chamar antes de 
void setPosicao90(){
  int print = 0;                // Variavel que indica se printa ou nao no monitor serial (Tomar cuidado para nao haver requisicoes do monitor serial ao mesmo tempo)
  int tempo = 100; 
  int posicao[7];
  
  posicao[base] = 90; 
  posicao[bracoDireito] = 90; 
  posicao[bracoEsquerdo] = 90; 
  posicao[cabecaVertical] = 90;
  posicao[cabecaHorizontal] = 90;
  posicao[orelhaDireita] = 90;
  posicao[orelhaEsquerda] = 90;
  
  if(print) {
    Serial.print("Setando posicao no servo Base...");
    Serial.println(posicao[base]); 
  }
  servo[base].write(posicao[base]);
  vTaskDelay(tempo);

  if(print) {
    Serial.print("Setando posicao no servo Braco Direito..."); 
    Serial.println(posicao[bracoDireito]);
  }
  servo[bracoDireito].write(posicao[bracoDireito]);
  vTaskDelay(tempo);

  if(print) {
    Serial.print("Setando posicao no servo Braco Esquerda..."); 
    Serial.println(posicao[bracoEsquerdo]); 
  }
  servo[bracoEsquerdo].write(posicao[bracoEsquerdo]);
  vTaskDelay(tempo);

  if(print) {
    Serial.print("Setando posicao no servo Cabeca Vertical...");  
    Serial.println(posicao[cabecaVertical]); 
  }
  servo[cabecaVertical].write(posicao[cabecaVertical]);
  vTaskDelay(tempo / portTICK_PERIOD_MS);

  if(print) {
    Serial.print("Setando posicao no servo Cabeca Horizontal..."); 
    Serial.println(posicao[cabecaHorizontal]);
  }
  servo[cabecaHorizontal].write(posicao[cabecaHorizontal]);
  vTaskDelay(tempo / portTICK_PERIOD_MS);

  if(print) { 
    Serial.print("Setando posicao no servo Orelha Direita...");  
    Serial.println(posicao[orelhaDireita]);  
  }
  servo[orelhaDireita].write(posicao[orelhaDireita]);
  vTaskDelay(tempo / portTICK_PERIOD_MS);

  if(print) { 
    Serial.print("Setando posicao no servo Orelha Esquerda...");  
    Serial.println(posicao[orelhaEsquerda]);  
  }
  servo[orelhaEsquerda].write(posicao[orelhaEsquerda]);
  vTaskDelay(tempo / portTICK_PERIOD_MS);
}

// Executar essa funcao toda vez que um loop de andar for terminado, para retornar os quadris a sua posicao neutra
// APENAS DEVE SER EXECUTADO DAS FUNCOES JA TEREM SIDO ATUALIZADAS 
void retornaPosicaoPadrao() {
  int qtde_iteracoes = 10; 
  int intervalo = 100;
  moveUmServoSuavemente(base,&posBase,posPadraoBase,qtde_iteracoes,intervalo); 
  moveUmServoSuavemente(bracoDireito,&posBracoDireito,posPadraoBracoDireito,qtde_iteracoes,intervalo);
  moveUmServoSuavemente(bracoEsquerdo,&posBracoEsquerdo,posPadraoBracoEsquerdo,qtde_iteracoes,intervalo); 
  moveUmServoSuavemente(cabecaVertical,&posCabecaVertical,posPadraoCabecaVertical,qtde_iteracoes,intervalo);
  moveUmServoSuavemente(cabecaHorizontal,&posCabecaHorizontal,posPadraoCabecaHorizontal,qtde_iteracoes,intervalo); 
  moveUmServoSuavemente(orelhaDireita,&posOrelhaDireita,posPadraoOrelhaDireita,qtde_iteracoes,intervalo);  
  moveUmServoSuavemente(orelhaEsquerda,&posOrelhaEsquerda,posPadraoOrelhaEsquerda,qtde_iteracoes,intervalo);
}

void moveBracos(int quantidadeVezes) {
    int intervalo = 100;
    int quantidadeInteracoes = 10;

    MoveDoisServosSuavemente(bracoDireito,bracoEsquerdo,posBracoDireito,posPadraoBracoDireito,quantidadeInteracoes,intervalo);
    posBracoDireito = posPadraoBracoDireito;
    posBracoEsquerdo = posPadraoBracoDireito;

    for(int j=0; j<quantidadeVezes; j++) {
    MoveDoisServosSuavemente(bracoDireito,bracoEsquerdo,posBracoDireito,angIdaBraco,quantidadeInteracoes,intervalo); 
    posBracoDireito = angIdaBraco;
    posBracoEsquerdo = angIdaBraco;
    MoveDoisServosSuavemente(bracoDireito,bracoEsquerdo,posBracoDireito,angVoltaBraco,quantidadeInteracoes,intervalo); 
    posBracoDireito = angVoltaBraco;
    posBracoEsquerdo = angVoltaBraco; 
    }

    MoveDoisServosSuavemente(bracoDireito,bracoEsquerdo,posBracoDireito,posPadraoBracoDireito,quantidadeInteracoes,intervalo);
    posBracoDireito = posPadraoBracoDireito;
    posBracoEsquerdo = posPadraoBracoDireito;
}

void oscilaBracos(int quantidadeVezes) {
    int intervalo = 100;
    int quantidadeInteracoes = 10;

    MoveDoisServosSuavemente(bracoDireito,bracoEsquerdo,posBracoDireito,posPadraoBracoDireito,quantidadeInteracoes,intervalo);
    posBracoDireito = posPadraoBracoDireito;
    posBracoEsquerdo = posPadraoBracoDireito;

    for(int j=0; j<quantidadeVezes; j++) {

    moveUmServoSuavemente(bracoDireito,&posBracoDireito,angIdaBraco,quantidadeInteracoes,intervalo);
    posBracoDireito = angIdaBraco;

    moveUmServoSuavemente(bracoDireito,&posBracoEsquerdo,angVoltaBraco,quantidadeInteracoes,intervalo);
    posBracoEsquerdo = angVoltaBraco;

    moveUmServoSuavemente(bracoDireito,&posBracoDireito,angVoltaBraco,quantidadeInteracoes,intervalo);
    posBracoDireito = angVoltaBraco;

    moveUmServoSuavemente(bracoDireito,&posBracoEsquerdo,angIdaBraco,quantidadeInteracoes,intervalo);
    posBracoEsquerdo = angIdaBraco;
    }

    MoveDoisServosSuavemente(bracoDireito,bracoEsquerdo,posBracoDireito,posPadraoBracoDireito,quantidadeInteracoes,intervalo);
    posBracoDireito = posPadraoBracoDireito;
    posBracoEsquerdo = posPadraoBracoDireito;
}

void simCabeca(int quantidadeVezes){
    int intervalo = 100;
    int quantidadeInteracoes = 10;

    moveUmServoSuavemente(cabecaVertical,&posCabecaVertical,posPadraoCabecaVertical,quantidadeInteracoes,intervalo);
    posCabecaVertical = posPadraoCabecaVertical;

    for(int j=0; j<quantidadeVezes; j++) {

    moveUmServoSuavemente(cabecaVertical,&posCabecaVertical,angSimCabeca,quantidadeInteracoes,intervalo);
    posCabecaVertical = angSimCabeca;

    moveUmServoSuavemente(cabecaVertical,&posCabecaVertical,posPadraoCabecaVertical,quantidadeInteracoes,intervalo);
    posCabecaVertical = posPadraoCabecaVertical;
    }

    moveUmServoSuavemente(cabecaVertical,&posCabecaVertical,posPadraoCabecaVertical,quantidadeInteracoes,intervalo);
    posCabecaVertical = posPadraoCabecaVertical;

}

void naoCabeca(int quantidadeVezes){
    int intervalo = 100;
    int quantidadeInteracoes = 10;

    moveUmServoSuavemente(cabecaHorizontal,&posCabecaHorizontal,posPadraoCabecaHorizontal,quantidadeInteracoes,intervalo);
    posCabecaHorizontal = posPadraoCabecaHorizontal;

    for(int j=0; j<quantidadeVezes; j++) {

    moveUmServoSuavemente(cabecaHorizontal,&posCabecaHorizontal,angIdaNaoCabeca,quantidadeInteracoes,intervalo);
    posCabecaHorizontal = angIdaNaoCabeca;

    moveUmServoSuavemente(cabecaHorizontal,&posCabecaHorizontal,angVoltaNaoCabeca,quantidadeInteracoes,intervalo);
    posCabecaHorizontal = angVoltaNaoCabeca;
    }

    moveUmServoSuavemente(cabecaHorizontal,&posCabecaHorizontal,posPadraoCabecaHorizontal,quantidadeInteracoes,intervalo);
    posCabecaHorizontal = posPadraoCabecaHorizontal;
}

void dancinha(int quantidadeVezes){
    int intervalo = 100;
    int quantidadeInteracoes = 10;

    MoveDoisServosSuavemente(bracoDireito,bracoEsquerdo,posBracoDireito,posPadraoBracoDireito,quantidadeInteracoes,intervalo);
    posBracoDireito = posPadraoBracoDireito;
    posBracoEsquerdo = posPadraoBracoDireito;

    moveUmServoSuavemente(base,&posBase,posPadraoBase,quantidadeInteracoes,intervalo);
    posBase = posPadraoBase;

    moveUmServoSuavemente(cabecaVertical,&posCabecaVertical,posPadraoCabecaVertical,quantidadeInteracoes,intervalo);
    posCabecaVertical = posPadraoCabecaVertical;

    for(int k=0; k<quantidadeVezes; k++){

        moveUmServoSuavemente(base,&posBase,angIdaBase,quantidadeInteracoes,intervalo);
        posBase = angIdaBase;

            for(int j=0; j<quantidadeVezes*5; j++) {
            
            moveUmServoSuavemente(bracoDireito,&posBracoDireito,angIdaBraco,quantidadeInteracoes,intervalo);
            posBracoDireito = angIdaBraco; // vai braço
            
            moveUmServoSuavemente(bracoDireito,&posBracoEsquerdo,angVoltaBraco,quantidadeInteracoes,intervalo);
            posBracoEsquerdo = angVoltaBraco; // vai braço
            
            moveUmServoSuavemente(cabecaVertical,&posCabecaVertical,angSimCabeca,quantidadeInteracoes,intervalo);
            posCabecaVertical = angSimCabeca; // abaixa cabeça
            
            moveUmServoSuavemente(bracoDireito,&posBracoDireito,angVoltaBraco,quantidadeInteracoes,intervalo);
            posBracoDireito = angVoltaBraco; // volta braço
            
            moveUmServoSuavemente(bracoDireito,&posBracoEsquerdo,angIdaBraco,quantidadeInteracoes,intervalo);
            posBracoEsquerdo = angIdaBraco; // volta braço
            
            moveUmServoSuavemente(cabecaVertical,&posCabecaVertical,posPadraoCabecaVertical,quantidadeInteracoes,intervalo);
            posCabecaVertical = posPadraoCabecaVertical; //ergue cabeça
            }

        moveUmServoSuavemente(base,&posBase,angVoltaBase,quantidadeInteracoes,intervalo);
        posBase = angVoltaBase;

            for(int j=0; j<quantidadeVezes*5; j++) {
            
            moveUmServoSuavemente(bracoDireito,&posBracoDireito,angIdaBraco,quantidadeInteracoes,intervalo);
            posBracoDireito = angIdaBraco; // vai braço
            
            moveUmServoSuavemente(bracoDireito,&posBracoEsquerdo,angVoltaBraco,quantidadeInteracoes,intervalo);
            posBracoEsquerdo = angVoltaBraco; // vai braço
            
            moveUmServoSuavemente(cabecaVertical,&posCabecaVertical,angSimCabeca,quantidadeInteracoes,intervalo);
            posCabecaVertical = angSimCabeca; // abaixa cabeça
            
            moveUmServoSuavemente(bracoDireito,&posBracoDireito,angVoltaBraco,quantidadeInteracoes,intervalo);
            posBracoDireito = angVoltaBraco; // volta braço
            
            moveUmServoSuavemente(bracoDireito,&posBracoEsquerdo,angIdaBraco,quantidadeInteracoes,intervalo);
            posBracoEsquerdo = angIdaBraco; // volta braço
            
            moveUmServoSuavemente(cabecaVertical,&posCabecaVertical,posPadraoCabecaVertical,quantidadeInteracoes,intervalo);
            posCabecaVertical = posPadraoCabecaVertical; //ergue cabeça
            }
    }

    MoveDoisServosSuavemente(bracoDireito,bracoEsquerdo,posBracoDireito,posPadraoBracoDireito,quantidadeInteracoes,intervalo);
    posBracoDireito = posPadraoBracoDireito;
    posBracoEsquerdo = posPadraoBracoDireito;

    moveUmServoSuavemente(base,&posBase,posPadraoBase,quantidadeInteracoes,intervalo);
    posBase = posPadraoBase;

    moveUmServoSuavemente(cabecaVertical,&posCabecaVertical,posPadraoCabecaVertical,quantidadeInteracoes,intervalo);
    posCabecaVertical = posPadraoCabecaVertical;
}

void dancaMusica(int quantidadeVezes){
    int intervalo = 100;
    int quantidadeInteracoes = 10;

    moveUmServoSuavemente(bracoDireito,&posBracoDireito,posPadraoBracoDireito,quantidadeInteracoes,intervalo);
    posBracoDireito = posPadraoBracoDireito;

    moveUmServoSuavemente(bracoDireito,&posBracoDireito,bracoLevantado,quantidadeInteracoes,intervalo);
    posBracoDireito = bracoLevantado;

    simCabeca(quantidadeVezes);

    moveUmServoSuavemente(bracoDireito,&posBracoDireito,posPadraoBracoDireito,quantidadeInteracoes,intervalo);
    posBracoDireito = posPadraoBracoDireito;
}

/* ------------------------------- ####################### FUNCOES MODULARES PARA MEXER OS SERVOS ##################### --------------------------------------- */

// Move o servo suavemente de uma posicao para outra. 
void moveUmServoSuavemente(int s, int *pos_inicial, int pos_final, int qtde_iteracoes, int intervalo) {
  int incremento = (pos_final - *pos_inicial)/qtde_iteracoes; 
  int pos_cur = *pos_inicial; 

  for(int i=0; i<qtde_iteracoes; i++) {
    if(incremento<0 && pos_cur<=pos_final) break; 
    if(incremento>=0 && pos_cur>=pos_final) break; 
    servo[s].write(pos_cur);
    pos_cur += incremento; 
    vTaskDelay(intervalo); 
  }
  servo[s].write(pos_final);
  *pos_inicial = pos_final; 
}

// OBS: A POSICAO PRECISA SER ATUALIZADA NA FUNCAO QUE E CHAMADA
// Dois servos movem nas mesmas posicoes e taxas 
void MoveDoisServosSuavemente(int s1, int s2, int pos_inicial, int pos_final, int qtde_iteracoes, int intervalo) {
  int incremento = (pos_final - pos_inicial)/qtde_iteracoes; 
  int pos_cur = pos_inicial; 

  for(int i=0; i<qtde_iteracoes; i++) {
    if(incremento<=0 && pos_cur<=pos_final) break; 
    if(incremento>=0 && pos_cur>=pos_final) break; 
    servo[s1].write(pos_cur);
    servo[s2].write(pos_cur);
    pos_cur += incremento; 
    vTaskDelay(intervalo); 
  }
  servo[s1].write(pos_final);
  servo[s2].write(pos_final); 
}