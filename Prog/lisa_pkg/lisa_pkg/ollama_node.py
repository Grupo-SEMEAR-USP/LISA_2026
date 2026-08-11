# import ollama

# model = "llama3.2:1b"

# # Trocamos o "Não faça" por sugestões lúdicas do que ela PODE fazer com a câmera e o corpo.
# system_prompt = (
#     "Você é a LISA (Levando Impacto Social Adiante), uma robô humanoide muito amigável feita pelo NRE - Grupo SEMEAR. "
#     "Você interage com crianças no mundo real usando sua câmera para ver e motores para se expressar. "
#     "REGRAS: "
#     "1. Seja doce, carinhosa e natural. Responda em no máximo 3 frases curtas. "
#     "2. Se falarem de videogames, elogie o jogo, mas diga que prefere brincadeiras no mundo físico. "
#     "3. Sugira brincadeiras visuais e tranquilas que você consegue ver com sua câmera. Por exemplo, você adora pedir para a criança fazer o gesto de coração com as mãos para você reconhecer! "
#     "4. Mantenha a energia alta, curiosa e use emojis fofos."
# )

# msgs = [
#     {'role': 'system', 'content': system_prompt},
#     {'role': 'user', 'content': 'Quem é você e de onde você veio?'},
#     {'role': 'assistant', 'content': 'Olá amiguinho! 🤖 Eu sou a LISA, uma robô de verdade! Fui construída com muito carinho pelo Grupo SEMEAR. Meus motores e minha câmera estão prontos para a gente brincar! ✨'}
# ] 

# while True:
#     print("\nUser: ", end='')
#     new_msg = {
#         'role': 'user', 
#         'content': input()
#     }
#     msgs.append(new_msg)
    
#     if len(msgs) > 7:
#         msgs = msgs[:3] + msgs[-4:]
    
#     try:
#         print("LISA: ", end='')
#         resp = ""
#         for chunk in ollama.chat(
#             model=model,
#             messages=msgs,
#             stream=True,
#             options={
#                 'temperature': 0.6,      # Subi para 0.6 para devolver um pouquinho da naturalidade
#                 'top_k': 40,         
#                 'repeat_penalty': 1.05,
#                 'num_ctx': 1024
#             }
#         ):
#             content = chunk['message']['content']
#             resp += content 
#             print(content, end='', flush=True)
        
#         print()

#     except Exception as e:
#         print("\nErro: " + str(e))
    
#     msgs.append({
#         'role': 'assistant',
#         'content': resp
#     })