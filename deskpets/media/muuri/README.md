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


## Escala 2x — 16/10/2026

Todos os sete estados ativos foram ampliados exatamente 2x a partir dos GIFs
anteriores: canvas de 80x64 para 160x128, mantendo o mesmo número de frames,
os tempos por frame, o loop, a transparência e o conteúdo de cada pixel. A
ampliação usa pixels inteiros para preservar o desenho pixelado e as cores.
O tamanho `Original` passa a ter 128 px de altura. Os tamanhos fixos Pequeno,
Médio, Grande e Bem grande continuam usando as alturas próprias do aplicativo.
As fontes originais foram guardadas fora do repositório durante a revisão.

## Estilo liso alternativo

A primeira versão da opção **Liso** suavizava os GIFs pixelados por reamostragem
Lanczos. Essa versão foi substituída em 24/10/2026 pelos assets descritos abaixo.

## Liso redesenhado — 24/10/2026

Os sete estados `idle`, `walk`, `walk_fast`, `run`, `swipe`, `lie` e `drag`
agora usam `blue_smooth_<estado>_8fps.png`: PNGs animados (APNG), com oito
frames RGBA, 125 ms por frame e loop contínuo. Canvas comum de **160x128 px**;
o tamanho Original continua com 128 px de altura. Não são PNGs estáticos.

A arte foi gerada em resolução maior a partir da referência canônica e de
uma única base da Muuri: corpo branco, manchas azuis, cascos azul-marinho,
chifres creme, focinho claro e ponta verde na cauda. O novo desenho usa
contornos curvos reais, em vez de ampliar e filtrar os sprites pixelados.
As bordas preservam níveis intermediários de alpha, que o GIF não suporta.

O fluxo da skill `work-pets:create-pet` foi adaptado ao DeskPets: uma base,
uma sequência por estado, extração por componentes, inspeção dos frames e
normalização comum de escala e baseline. Os scripts oficiais de extração e
inspeção foram executados com a geometria de trabalho 640x512 e os sete
estados do aplicativo, sem modificar a skill instalada. A conversão final
apenas enquadra e reduz os pixels gerados; não desenha partes do personagem.
Não há atlas de ChatGPT, upload nem animações extras de direção.

O carregador Pillow, a prévia Qt e os renderizadores existentes já aceitam
APNG: nenhuma troca de engine foi necessária. O catálogo aponta somente
o estilo Liso para os novos arquivos. Os GIFs `blue_<estado>_8fps.gif` do
estilo **Pixelado**, os outros pets, os parâmetros de movimento/física e
as preferências locais foram preservados. Uma correção na seleção do
estado de descanso impede a volta involuntária ao asset pixelado quando
o cursor se aproxima.

Espelhamento esquerda/direita continua no engine; não há assets duplicados.
As margens são transparentes e a cauda verde é opaca em todos os frames.
O descanso mantém os cascos na mesma linha dos estados no chão; o arraste
usa uma posição suspensa. Por serem sequências generativas, ainda podem
existir pequenas variações de traço entre frames, sujeitas à revisão visual.

Para escolher, abra o painel, selecione Muuri, escolha **Liso** e clique em
**Aplicar**. Licença e créditos originais permanecem válidos.
