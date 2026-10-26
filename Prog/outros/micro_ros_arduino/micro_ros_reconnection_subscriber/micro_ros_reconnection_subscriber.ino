#include <micro_ros_arduino.h>

#include <stdio.h>
#include <string.h>
#include <rcl/rcl.h>
#include <rcl/error_handling.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <rmw_microros/rmw_microros.h>

#include <example_interfaces/msg/string.h>

#define LED_STATUS 2
#define LED_PIN 4
#define BUFFER_LENGTH 64

#define RCCHECK(fn) { rcl_ret_t temp_rc = fn; if((temp_rc != RCL_RET_OK)){return false;}}
#define EXECUTE_EVERY_N_MS(MS, X)  do { \
  static volatile int64_t init = -1; \
  if (init == -1) { init = uxr_millis();} \
  if (uxr_millis() - init > MS) { X; init = uxr_millis();} \
} while (0)\

rclc_support_t support;
rcl_node_t node;
rclc_executor_t executor;
rcl_allocator_t allocator;
rcl_subscription_t subscriber;
rcl_publisher_t log_publisher;

example_interfaces__msg__String msg;      // mensagem recebida (visao/gestos)
example_interfaces__msg__String log_msg;  // mensagem enviada (esp32/log)

// Buffers estaticos: o micro-ROS escreve/le direto neles.
static char rx_buffer[BUFFER_LENGTH];
static char tx_buffer[BUFFER_LENGTH];

enum states {
  WAITING_AGENT,
  AGENT_AVAILABLE,
  AGENT_CONNECTED,
  AGENT_DISCONNECTED
} state;

// Publica uma string em esp32/log (so quando conectado ao agente).
void log_info(const char * info)
{
  if (info == NULL || state != AGENT_CONNECTED) {
    return;
  }

  strncpy(tx_buffer, info, BUFFER_LENGTH - 1);
  tx_buffer[BUFFER_LENGTH - 1] = '\0';
  log_msg.data.size = strlen(tx_buffer);

  (void) rcl_publish(&log_publisher, &log_msg, NULL);
}

void subscription_callback(const void * msgin)
{
  const example_interfaces__msg__String * received =
    (const example_interfaces__msg__String *)msgin;

  const char * gesture = received->data.data;

  log_info(gesture);
  
  digitalWrite(LED_PIN, (strcmp(gesture, "like") == 0) ? HIGH : LOW);
}

// Functions create_entities and destroy_entities can take several seconds.
// In order to reduce this rebuild the library with
// - RMW_UXRCE_ENTITY_CREATION_DESTROY_TIMEOUT=0
// - UCLIENT_MAX_SESSION_CONNECTION_ATTEMPTS=3

bool create_entities()
{
  allocator = rcl_get_default_allocator();

  // create init_options
  RCCHECK(rclc_support_init(&support, 0, NULL, &allocator));

  // create node
  RCCHECK(rclc_node_init_default(&node, "micro_ros_reconnection_subscriber", "", &support));

  // create subscriber (visao/gestos)
  RCCHECK(rclc_subscription_init_best_effort(
    &subscriber,
    &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(example_interfaces, msg, String),
    "visao/gestos"));

  // create publisher (esp32/log)
  RCCHECK(rclc_publisher_init_default(
    &log_publisher,
    &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(example_interfaces, msg, String),
    "esp32/log"));

  // create executor
  executor = rclc_executor_get_zero_initialized_executor();
  RCCHECK(rclc_executor_init(&executor, &support.context, 1, &allocator));
  RCCHECK(rclc_executor_add_subscription(&executor, &subscriber, &msg, &subscription_callback, ON_NEW_DATA));

  return true;
}

void destroy_entities()
{
  rmw_context_t * rmw_context = rcl_context_get_rmw_context(&support.context);
  (void) rmw_uros_set_context_entity_destroy_session_timeout(rmw_context, 0);

  rcl_subscription_fini(&subscriber, &node);
  rcl_publisher_fini(&log_publisher, &node);
  rclc_executor_fini(&executor);
  rcl_node_fini(&node);
  rclc_support_fini(&support);
}

void setup() {
  set_microros_transports();

  pinMode(LED_STATUS, OUTPUT);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  // Buffers das mensagens String (alocacao estatica)
  msg.data.data = rx_buffer;
  msg.data.capacity = BUFFER_LENGTH;
  msg.data.size = 0;
  rx_buffer[0] = '\0';

  log_msg.data.data = tx_buffer;
  log_msg.data.capacity = BUFFER_LENGTH;
  log_msg.data.size = 0;
  tx_buffer[0] = '\0';

  state = WAITING_AGENT;
}

void loop() {
  switch (state) {
    case WAITING_AGENT:
      EXECUTE_EVERY_N_MS(500, state = (RMW_RET_OK == rmw_uros_ping_agent(100, 1)) ? AGENT_AVAILABLE : WAITING_AGENT;);
      break;
    case AGENT_AVAILABLE:
      state = (true == create_entities()) ? AGENT_CONNECTED : WAITING_AGENT;
      if (state == WAITING_AGENT) {
        destroy_entities();
      } else {
        log_info("ESP32 conectada");
      }
      break;
    case AGENT_CONNECTED:
      EXECUTE_EVERY_N_MS(200, state = (RMW_RET_OK == rmw_uros_ping_agent(100, 1)) ? AGENT_CONNECTED : AGENT_DISCONNECTED;);
      if (state == AGENT_CONNECTED) {
        rclc_executor_spin_some(&executor, RCL_MS_TO_NS(100));
      }
      break;
    case AGENT_DISCONNECTED:
      destroy_entities();
      digitalWrite(LED_PIN, LOW);
      state = WAITING_AGENT;
      break;
    default:
      break;
  }

  if (state == AGENT_CONNECTED) {
    digitalWrite(LED_STATUS, 1);
  } else {
    digitalWrite(LED_STATUS, 0);
  }
}