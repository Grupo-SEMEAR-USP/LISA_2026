#include <stddef.h>
#include <string.h>

#include "animacoes.h"
#include "acender_led.h"

// Tipos de ponteiros para as funções das animacoes.
typedef void (*FuncaoAnimacao)();
typedef bool (*EstadoAnimacao)();

// Estrutura que representa uma animacao.
struct Animacao {
    const char *nome;

    FuncaoAnimacao iniciar;
    FuncaoAnimacao atualizar;
    FuncaoAnimacao finalizar;

    EstadoAnimacao em_execucao;
};

// Registro de todas as animacoes disponiveis.
static const Animacao animacoes[] = {
    {
        "acender_led",
        iniciar_acender_led,
        atualizar_acender_led,
        finalizar_acender_led,
        acender_led_em_execucao
    }
};

// Quantidade de animacoes registradas.
static const size_t quantidade_animacoes =
    sizeof(animacoes) / sizeof(animacoes[0]);

// Ponteiro para a animacao atualmente selecionada.
static const Animacao *animacao_atual = nullptr;


// ============================================================
// INICIAR ANIMACAO
// ============================================================

bool iniciar_animacao(const char *nome) {

    // Impede iniciar uma nova animacao enquanto outra estiver ativa.
    if (animacao_atual != nullptr || nome == nullptr) {
        return false;
    }

    // Procura a animacao solicitada no registro.
    for (size_t i = 0; i < quantidade_animacoes; i++) {

        if (strcmp(nome, animacoes[i].nome) == 0) {

            animacao_atual = &animacoes[i];

            animacao_atual->iniciar();

            // Confirma se a animacao realmente iniciou.
            if (!animacao_atual->em_execucao()) {
                animacao_atual = nullptr;
                return false;
            }

            return true;
        }
    }

    // Nenhuma animacao correspondente foi encontrada.
    return false;
}


// ============================================================
// ATUALIZAR ANIMACAO
// ============================================================

bool atualizar_animacao() {

    // Nenhuma animacao ativa.
    if (animacao_atual == nullptr) {
        return false;
    }

    // Atualiza exclusivamente a animacao selecionada.
    animacao_atual->atualizar();

    // Verifica se a animacao terminou.
    if (!animacao_atual->em_execucao()) {

        animacao_atual = nullptr;

        return true;
    }

    return false;
}


// ============================================================
// FINALIZAR ANIMACAO
// ============================================================

void finalizar_animacao() {

    // Não há nada para finalizar.
    if (animacao_atual == nullptr) {
        return;
    }

    // Finaliza exclusivamente a animacao selecionada.
    animacao_atual->finalizar();

    animacao_atual = nullptr;
}


// ============================================================
// VERIFICAR ESTADO
// ============================================================

bool animacao_em_execucao() {
    return animacao_atual != nullptr;
}