#include <micro_ros_arduino.h>

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stdint.h>

#include <rcl/rcl.h>
#include <rcl/error_handling.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <rmw_microros/rmw_microros.h>

#include <std_msgs/msg/string.h>

// ============================================================
// CONFIGURACOES
// ============================================================

#define LED_STATUS 2
#define LED_PIN 4

#define BUFFER_LENGTH 64
#define ANIMATION_DURATION_MS 5000UL

#define ANIMATION_TOPIC "/esp32/solicitar_animacao"
#define RESPONSE_TOPIC "/esp32/resposta_animacao"
#define LOG_TOPIC "/esp32/log"

#define RCCHECK(fn) { \
  rcl_ret_t temp_rc = fn; \
  if ((temp_rc) != RCL_RET_OK) { \
    return false; \
  } \
}

#define EXECUTE_EVERY_N_MS(MS, X) do { \
  static volatile int64_t init = -1; \
  if (init == -1) { \
    init = uxr_millis(); \
  } \
  if (uxr_millis() - init > MS) { \
    X; \
    init = uxr_millis(); \
  } \
} while (0)

// ============================================================
// OBJETOS MICRO-ROS
// ============================================================

rclc_support_t support;
rcl_node_t node;
rclc_executor_t executor;
rcl_allocator_t allocator;

rcl_subscription_t animation_subscriber;

rcl_publisher_t response_publisher;
rcl_publisher_t log_publisher;

// Mensagens
std_msgs__msg__String request_msg;
std_msgs__msg__String response_msg;
std_msgs__msg__String log_msg;

// Buffers estaticos
static char rx_buffer[BUFFER_LENGTH];
static char response_buffer[BUFFER_LENGTH];
static char tx_buffer[BUFFER_LENGTH];

// Controle de inicializacao das entidades
bool support_initialized = false;
bool node_initialized = false;
bool subscriber_initialized = false;
bool response_publisher_initialized = false;
bool log_publisher_initialized = false;
bool executor_initialized = false;

// ============================================================
// ESTADO DA CONEXAO MICRO-ROS
// ============================================================

enum states {
  WAITING_AGENT,
  AGENT_AVAILABLE,
  AGENT_CONNECTED,
  AGENT_DISCONNECTED
};

states state;

// ============================================================
// CONTROLE DAS ANIMACOES
// ============================================================

bool animation_running = false;

uint32_t animation_end_time = 0;

// ============================================================
// PUBLICACAO DE MENSAGENS
// ============================================================

// Publica uma resposta associada ao identificador da requisicao.
void publish_response(uint32_t request_id, bool sucesso)
{
  if (state != AGENT_CONNECTED) {
    return;
  }

  snprintf(
    response_buffer,
    BUFFER_LENGTH,
    "%lu|%d",
    (unsigned long)request_id,
    sucesso ? 1 : 0
  );

  response_msg.data.size = strlen(response_buffer);

  (void) rcl_publish(&response_publisher, &response_msg, NULL);
}

// Publica uma string em /esp32/log.
void log_info(const char *info)
{
  if (info == NULL || state != AGENT_CONNECTED) {
    return;
  }

  strncpy(tx_buffer, info, BUFFER_LENGTH - 1);
  tx_buffer[BUFFER_LENGTH - 1] = '\0';

  log_msg.data.size = strlen(tx_buffer);

  (void) rcl_publish(&log_publisher, &log_msg, NULL);
}

// ============================================================
// CALLBACK DE SOLICITACAO DE ANIMACAO
// ============================================================

void animation_callback(const void *msgin)
{
  const std_msgs__msg__String *received =
    (const std_msgs__msg__String *)msgin;

  // Garante que a mensagem cabe no buffer.
  if (received->data.size >= BUFFER_LENGTH) {
    log_info("Requisicao recusada: mensagem muito longa");
    return;
  }

  rx_buffer[received->data.size] = '\0';

  // Separa o identificador do nome da animacao.
  char *separator = strchr(rx_buffer, '|');

  if (separator == NULL) {
    log_info("Requisicao invalida: identificador ausente");
    return;
  }

  *separator = '\0';

  // Converte o identificador para inteiro.
  char *endptr = NULL;

  unsigned long parsed_id = strtoul(rx_buffer, &endptr, 10);

  if (
    endptr == rx_buffer ||
    *endptr != '\0' ||
    parsed_id > UINT32_MAX
  ) {
    log_info("Requisicao invalida: identificador incorreto");
    return;
  }

  uint32_t request_id = (uint32_t)parsed_id;

  const char *animation = separator + 1;

  // Verifica se ja existe uma animacao em execucao.
  if (animation_running) {

    publish_response(request_id, false);

    log_info("Requisicao recusada: ESP32 ocupada");

    return;
  }

  // Verifica a animacao solicitada.
  if (strcmp(animation, "dancinha") == 0) {

    animation_running = true;

    animation_end_time = millis() + ANIMATION_DURATION_MS;

    digitalWrite(LED_PIN, HIGH);

    publish_response(request_id, true);

    log_info("Animacao dancinha iniciada");

  } else {

    publish_response(request_id, false);

    log_info("Requisicao recusada: animacao desconhecida");
  }
}

// ============================================================
// ATUALIZACAO DA ANIMACAO
// ============================================================

void update_animation()
{
  if (
    animation_running &&
    (int32_t)(millis() - animation_end_time) >= 0
  ) {

    animation_running = false;

    digitalWrite(LED_PIN, LOW);

    log_info("Animacao dancinha finalizada");
  }
}

// ============================================================
// CRIACAO DAS ENTIDADES MICRO-ROS
// ============================================================

// Functions create_entities and destroy_entities can take
// several seconds. In order to reduce this rebuild the library with
// -DRMW_UXRCE_ENTITY_CREATION_DESTROY_TIMEOUT=0
// -DUCLIENT_MAX_SESSION_CONNECTION_ATTEMPTS=3

bool create_entities()
{
  allocator = rcl_get_default_allocator();

  // Inicializa o suporte ROS.
  RCCHECK(
    rclc_support_init(
      &support,
      0,
      NULL,
      &allocator
    )
  );

  support_initialized = true;

  // Cria o no.
  RCCHECK(
    rclc_node_init_default(
      &node,
      "esp_lisa_micro_ros",
      "",
      &support
    )
  );

  node_initialized = true;

  // Cria o subscriber de solicitacoes de animacao.
  RCCHECK(
    rclc_subscription_init_default(
      &animation_subscriber,
      &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, String),
      ANIMATION_TOPIC
    )
  );

  subscriber_initialized = true;

  // Cria o publisher de respostas.
  RCCHECK(
    rclc_publisher_init_default(
      &response_publisher,
      &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, String),
      RESPONSE_TOPIC
    )
  );

  response_publisher_initialized = true;

  // Cria o publisher de logs.
  RCCHECK(
    rclc_publisher_init_default(
      &log_publisher,
      &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, String),
      LOG_TOPIC
    )
  );

  log_publisher_initialized = true;

  // Inicializa o executor.
  executor = rclc_executor_get_zero_initialized_executor();

  RCCHECK(
    rclc_executor_init(
      &executor,
      &support.context,
      1,
      &allocator
    )
  );

  executor_initialized = true;

  // Adiciona o subscriber ao executor.
  RCCHECK(
    rclc_executor_add_subscription(
      &executor,
      &animation_subscriber,
      &request_msg,
      &animation_callback,
      ON_NEW_DATA
    )
  );

  return true;
}

// ============================================================
// DESTRUICAO DAS ENTIDADES MICRO-ROS
// ============================================================

void destroy_entities()
{
  if (support_initialized) {

    rmw_context_t *rmw_context =
      rcl_context_get_rmw_context(&support.context);

    (void) rmw_uros_set_context_entity_destroy_session_timeout(
      rmw_context,
      0
    );
  }

  if (executor_initialized) {
    rclc_executor_fini(&executor);
    executor_initialized = false;
  }

  if (subscriber_initialized) {
    rcl_subscription_fini(&animation_subscriber, &node);
    subscriber_initialized = false;
  }

  if (response_publisher_initialized) {
    rcl_publisher_fini(&response_publisher, &node);
    response_publisher_initialized = false;
  }

  if (log_publisher_initialized) {
    rcl_publisher_fini(&log_publisher, &node);
    log_publisher_initialized = false;
  }

  if (node_initialized) {
    rcl_node_fini(&node);
    node_initialized = false;
  }

  if (support_initialized) {
    rclc_support_fini(&support);
    support_initialized = false;
  }
}

// ============================================================
// SETUP
// ============================================================

void setup()
{
  set_microros_transports();

  pinMode(LED_STATUS, OUTPUT);
  pinMode(LED_PIN, OUTPUT);

  digitalWrite(LED_STATUS, LOW);
  digitalWrite(LED_PIN, LOW);

  // Inicializa buffer das requisicoes.
  request_msg.data.data = rx_buffer;
  request_msg.data.capacity = BUFFER_LENGTH;
  request_msg.data.size = 0;

  rx_buffer[0] = '\0';

  // Inicializa buffer das respostas.
  response_msg.data.data = response_buffer;
  response_msg.data.capacity = BUFFER_LENGTH;
  response_msg.data.size = 0;

  response_buffer[0] = '\0';

  // Inicializa buffer dos logs.
  log_msg.data.data = tx_buffer;
  log_msg.data.capacity = BUFFER_LENGTH;
  log_msg.data.size = 0;

  tx_buffer[0] = '\0';

  state = WAITING_AGENT;
}

// ============================================================
// LOOP PRINCIPAL
// ============================================================

void loop()
{
  // Atualiza a animacao sem bloquear o loop.
  update_animation();

  switch (state) {

    case WAITING_AGENT:

      EXECUTE_EVERY_N_MS(
        500,
        state = (
          RMW_RET_OK == rmw_uros_ping_agent(100, 1)
        ) ? AGENT_AVAILABLE : WAITING_AGENT;
      );

      break;

    case AGENT_AVAILABLE:

      if (create_entities()) {

        state = AGENT_CONNECTED;

        log_info("ESP32 conectada");

      } else {

        destroy_entities();

        state = WAITING_AGENT;
      }

      break;

    case AGENT_CONNECTED:

      EXECUTE_EVERY_N_MS(
        200,
        state = (
          RMW_RET_OK == rmw_uros_ping_agent(100, 1)
        ) ? AGENT_CONNECTED : AGENT_DISCONNECTED;
      );

      if (state == AGENT_CONNECTED) {

        rclc_executor_spin_some(
          &executor,
          RCL_MS_TO_NS(100)
        );
      }

      break;

    case AGENT_DISCONNECTED:

      destroy_entities();

      // Interrompe a animacao em caso de desconexao.
      animation_running = false;

      digitalWrite(LED_PIN, LOW);

      state = WAITING_AGENT;

      break;

    default:

      break;
  }

  // Atualiza novamente apos o processamento do executor.
  update_animation();

  // LED de status indica conexao com o agente micro-ROS.
  digitalWrite(
    LED_STATUS,
    (state == AGENT_CONNECTED) ? HIGH : LOW
  );
}
