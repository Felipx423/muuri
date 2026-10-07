# Muuri — assets provisórios para revisão

Os seis GIFs blue_*_8fps.gif são animações geradas com a referência canônica
fornecida pelo usuário em 06/10/2026. Não são arte final aprovada.
Canvas 80x64, seis frames por estado, transparência, disposal=2, loop,
120/130 ms alternados; o engine usa fps e speed_animation do JSON.

Pendências visuais: pequenas variações de manchas/proporções; refinamento
de passadas e continuidade do loop; lie fica mais frontal que os outros
estados. Small redimensiona o canvas para 40 px e reduz a altura visível.
Não há arquivos separados para esquerda/direita. Nenhum asset original foi
reutilizado ou alterado. Créditos e licença originais permanecem no projeto.

Referência canônica SHA-256: 203a40003ad448fa5b8e8abc663a0674581449f636cb216f4cff75d98e9a0670

Revisao 06/10/2026: walk/walk_fast/run agora usam oito frames com anatomia fixa de pecas geradas. Quatro patas articuladas em pontos fixos, passada curta/pares diagonais/amplitude maior. Todos os 24 frames possuem um unico componente opaco conectado. Idle/lie/swipe permanecem intactos com seis frames. Nenhuma mudanca no engine.



## Correção atual das pernas — base arredondada

A base alongada de peças foi rejeitada pelo usuário e não é a versão ativa.
Os GIFs walk/walk_fast/run atuais usam a Muuri arredondada original como
alvo de edição, com correções concentradas nas pernas e cascos. Foram feitas
duas passagens de imagegen para melhorar separação e alternância das patas.
São seis frames por GIF, canvas 80x64 e timings originais. Idle, lie e swipe
permanecem byte a byte iguais ao backup anterior à correção. Nenhum JSON ou
Python do engine foi alterado nesta revisão. A frase anterior sobre oito
frames/peças fixas descreve uma versão descartada, não os assets ativos.
Cabeça, corpo, manchas, chifres e cauda mantêm a aparência arredondada;
a geração não garante identidade pixel a pixel com os frames originais.


## Animação durante o arraste

Adicionado blue_drag_8fps.gif: oito frames, canvas 80x64, transparência,
loop e 8 fps (120/130 ms alternados). Aparência baseada na Muuri arredondada
ativa e na referência canônica. Patas suspensas com pequenas flexões.
Os seis GIFs anteriores não foram substituídos nesta etapa.

A skill work-pets:create-pet foi adaptada para gerar uma sequência isolada,
sem upload ao ChatGPT e sem mudar o formato do DeskPets. Imagegen editou as
referências; os scripts oficiais extract_strip_frames.py e inspect_frames.py
extraíram/verificaram os oito componentes sem erros nem alertas. O nome
running-right é apenas a chave de transporte de oito frames desses scripts:
o estado do DeskPets chama-se drag e não executa corrida. Conversão posterior
aplica uma única escala e enquadramento comum, sem desenhar partes à mão.
Como edição generativa, não se afirma identidade pixel a pixel entre poses.

pets_data.json define drag exclusivamente para Muuri. A integração Python
é genérica: durante o arraste, usa drag se disponível; acompanha o sentido
horizontal com o espelhamento já existente; ao soltar restaura estado e
contador anteriores. drag fica excluído da seleção aleatória. Pets sem esse
asset mantêm o comportamento de pausa. A troca de frames ocorre no worker,
e não no callback do mouse. O tamanho Original escolhido foi preservado.

Testes: oito frames nas duas direções pelo PetWorker e renderização nativa;
clique/captura/movimento/soltura; transparência e margens; sete estados;
restauração de estado; exclusão aleatória; espécie sem drag; timer Qt,
seleção, tamanho e recarga. Todos passaram. O teste da janela de configurações
substitui somente o navegador de créditos por QWidget para isolar rede/WebEngine;
isso não altera o aplicativo. A sensação visual final ao usar o mouse cabe
à revisão do usuário. Nenhum commit ou push realizado.


## Correção da transparência da cauda no arraste

A extração anterior aplicava chroma key verde (#00FF00, tolerância 96) mesmo
com a imagem original já transparente. Isso apagava o preenchimento verde da
ponta da cauda. A extração foi refeita a partir da mesma imagem original,
com chave magenta ausente no desenho (#FF00FF, tolerância zero), preservando
o canal alfa existente. Não houve redesenho nem alteração do engine.

O GIF mantém oito frames, 80x64, loop, disposal=2, margens e 120/130 ms.
A ponta agora possui 54–58 pixels verdes opacos por frame; antes eram 7–17,
restritos principalmente às bordas. Dois testes específicos verificam a cor
opaca da cauda em todos os frames e os parâmetros/transparência do GIF.
A validação de extração da skill passou sem erros nem alertas.

Hashes confirmaram que os outros seis GIFs, pets_data.json e pets_list.json
permanecem iguais aos anteriores a esta correção. A prévia muuri-arraste.gif
foi atualizada. Reinicie a instância antiga para recarregar os frames.
Sem commit ou push.
