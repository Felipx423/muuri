# Histórico de desenvolvimento da Muuri

> Este documento é um histórico técnico de etapas intermediárias, incluindo
> alternativas descartadas. Não é a documentação principal. Para instalação e
> uso atual, consulte [README.md](README.md).
> As pendências, versões e menções a ausência de commit abaixo descrevem o
> momento de cada marco; não representam necessariamente o estado atual.

## Marco inicial: integração de trabalho

Branch: `feat/muuri-pet`. Origem: https://github.com/Jumitti/DeskPets,
commit `d1d00fc137c9494bb2de0cc660cd5915b1be0034`.

## Análise e plano antes da edição

O README e os arquivos pets_data.json, pets_list.json, pets.py, state.py,
petworker.py, window.py e media foram lidos antes de editar.
Plano: adicionar somente JSON, seis GIFs temporários e documentação;
validar com o carregador, os estados e o renderer existentes.

- `load_pets` lê `pets_list.json`, ignora entradas desabilitadas e cria um
  `Pet` por cor. FPS padrão: 8. O seletor enumera `pets_data.json`.
- `Pet` monta STATES_INFO pelos paths e defaults do JSON. O estado inicial
  e as transições são aleatórios. `hold` conta atualizações, não segundos.
- `GifHelper` resolve paths relativos ao pacote, decodifica com Pillow em
  RGBA e inverte verticalmente para a convenção do renderer Windows.
- A animação avança um frame a cada `1/(fps * speed_animation)` segundo;
  a duração codificada no GIF não governa o engine.
- `State.next` soma `movement_speed * direction` à posição horizontal em
  cada atualização. Os limites de tela e o quarto direito da tela em Pet
  provocam inversões de direção. `lie` também pode ser ativado por proximidade
  do cursor; essa rota usa `lie_duration=24`, já compatível com a configuração.
- O worker espelha horizontalmente quando `direction < 0`. Os assets finais
  devem olhar para a direita. Não são necessários GIFs para cada direção.
- `Small` redimensiona TODO o canvas para 40 px de altura com LANCZOS,
  preservando a proporção. Margens reduzem a altura visível. Não existe
  tamanho personalizado de 64 px no engine atual. `Original` usa o canvas
  original, uma alternativa para avaliar assets finais sem mudar o engine.
- `window.py` desenha uma janela layered Windows com alpha por pixel.
  O helper converte para BGRA premultiplicado. Nenhum Python foi alterado.

## Assets gerados para revisão visual

A referência canônica foi recebida durante a execução. A imagem anexada é
uma prancha de nove poses da mesma vaca Muuri. As seis animações foram
geradas separadamente com essa referência e convertidas para GIF; não são
um atlas ChatGPT Work e não requerem alterações do engine.

Os cartões TEMP iniciais foram substituídos. Os GIFs atuais são **versões
provisórias para revisão visual**, não arte final aprovada: existem pequenas
variações de manchas/proporções entre poses. As passadas de walk_fast/run
precisam de refinamento artístico para garantir anatomia perfeitamente
estável, continuidade do loop e pares de patas naturais. Lie tende a uma
vista mais frontal. Idle inclui piscada e movimento discreto, swipe levanta
uma pata, e lie apresenta descanso com piscada. Nenhum GIF final falta como
arquivo; a aprovação/refinamento visual dos seis ainda está pendente.

Todos têm canvas 80x64, seis frames, transparência real, margens e baseline
comum. Os poses foram extraídos pelos intervalos de alpha e seus espaços
transparentes, em vez de cortar a prancha em células presumidas. Uma escala
única foi aplicada a todos os estados. Loop infinito, disposal=2, duração
alternada 120/130 ms (média 125 ms, 8 fps); o engine aplica suas velocidades.
Foram inspecionados todos os 36 frames em uma folha de contato.

Small é o canvas de 40 px; a altura opaca visível é menor. A referência
continua sendo autoridade visual. Os renders são candidatos derivados dela.
O ícone é opcional e ainda não foi criado: o seletor mostra `[no icon]`.

## Ambiente e execução

Na raiz deste clone, em PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

`run.py` já pertence ao projeto. O gerenciador inicia escondido na bandeja;
usar Show/Refresh/Quit no ícone DeskPets. Fechar o gerenciador apenas minimiza.
Não foi instalado um launcher novo nem pacotes globais.

## Licença e créditos

LICENSE (MIT, Copyright 2025 Minniti Julien), README e créditos originais
permanecem intactos. DeskPets é inspirado em vscode-pets, de tonybaloney;
os créditos e restrições dos assets originais continuam aplicáveis.
Os GIFs da Muuri são novos, derivados da referência fornecida pelo usuário
usando imagegen, e são acrescentados sob a mesma licença MIT. A referência canônica foi fornecida pelo usuário nesta conversa;
a aprovação final dos assets derivados está pendente.

Nenhum commit ou push foi feito. Consultar o relatório de revisão para os
resultados medidos e as limitações do teste de desktop.

## Revisao das passadas - 06/10/2026
Walk, walk_fast e run foram substituidos por oito frames montados com um tronco e quatro patas fixos gerados de acordo com a referencia. Idle, lie e swipe continuam com seis frames e bytes intactos. As partes sao articuladas durante a preparacao dos GIFs, fora do engine. Testes de conectividade nos 24 frames, movimento, renderer, espelhamento e launcher Windows passaram. O run e uma passada estilizada mais ampla; nao simula um galope detalhado. O relatorio atualizado esta em outputs/PASSADAS_MUURI_REVISAO.md na pasta de trabalho superior. Esta revisao substitui as observacoes anteriores sobre regeneracao de walk/walk_fast/run.



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

## Atualização: arraste com o mouse

Após pedido explícito do usuário, foi acrescentado suporte genérico a
`draggable`, habilitado para Muuri em pets_list.json. Isso exige os ajustes
pequenos em windows_API.py, pets.py, petworker.py, window.py e selector.py:
receber cliques, capturar o mouse, pausar o deslocamento e manter a posição
ao soltar. A arquitetura e os assets permanecem os mesmos. As afirmações
anteriores de Python intacto descrevem as etapas de integração por assets,
antes desta funcionalidade. O tamanho Original atual foi preservado.

Segure o botão esquerdo sobre o pet, arraste e solte. A posição vale para
a sessão e para a tela principal; Refresh ou reiniciar recria o pet no canto.
Os testes de eventos nativos, transparência, captura, timer Qt, conservação
do flag nos settings e encerramento durante arraste passaram. Detalhes no
relatório MUURI_ARRASTAVEL.md em outputs da conversa. Sem commit ou push.


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


## Painel de configuração — 7 de outubro de 2026

Painel PyQt em português, claro e azul, com Pets, Preferências e Créditos.
Quatro cliques completos em até 1,5 segundo abrem a mesma janela. Movimento
maior que seis pixels durante um clique cancela a sequência. A Muuri fica
parada brevemente entre cliques para continuar sob o ponteiro. O gesto é
configurado por settings_clicks=4 em pets_list.json e funciona com arraste
ligado ou desligado; outras espécies continuam com seu comportamento original.

Ativação, cores, seis tamanhos com altura do canvas, arraste e multiplicadores
independentes (movement_multiplier e animation_multiplier, 0.5–2.0) ficam por
espécie em pets_list.json. Campos ausentes usam 1.0. A camada permanece em
config.json. O tamanho Original, os sete GIFs da Muuri, pets_data.json,
licença e créditos existentes foram preservados nesta etapa.

A prévia usa os próprios GIFs, transparência quadriculada, estado e direção.
Pode ser ampliada/ajustada ao painel; a legenda informa o canvas real em px.
Alterar a prévia não salva nem muda os pets. Aplicar faz a gravação; Descartar
restaura os valores salvos. Fechar com alterações oferece três escolhas.
Os arquivos são preparados antes da substituição e uma falha recuperável
restaura os anteriores. Erros ficam visíveis e o rascunho permanece disponível.
Campos desconhecidos e configurações das espécies não editadas são preservados.

Movimento e simulação mantêm a cadência original de cada estado; reprodução
GIF tem seu próprio relógio. Assim, velocidade da animação não encurta os
estados nem acelera o deslocamento. O multiplicador de movimento também é
respeitado nas cenas do esquilo. Ao aplicar, o worker anterior é encerrado e
aguardado; posição, altura e orientação são recuperadas para pets que continuam
ativos. Coordenadas fracionárias são convertidas somente ao desenhar no Windows.

A aba Créditos apresenta os créditos originais e a licença MIT localmente,
com links para DeskPets e vscode-pets, sem depender de abrir um navegador
embutido. Os módulos antigos permanecem disponíveis; o launcher é o mesmo.
O aplicativo inicia oculto na bandeja. Fechar o painel não encerra os pets.

Correções identificadas durante esta integração: GIFs abertos são fechados
explicitamente; fallback da barra de tarefas retorna os três valores esperados;
atualização por tela cheia é adiada para evitar destruir a janela no desenho.
Em 150% há rolagem para acessar os controles; em 100% e 125% cabem integralmente.

Testes: tests/test_settings_panel.py (20 cenários), launcher original run.py
por oito segundos, capturas e inspeção visual em 100%, 125% e 150%. Incluem
cliques lentos, duplos cliques, arraste, estados, tamanhos, prévias das espécies,
salvamento, descarte, falhas e rollback, reinício, campos extras, movimento,
duração dos estados, outros pets e finalização do worker. Sem commit ou push.


## Correção da troca de pet pelo painel

A seleção na lista anteriormente mudava apenas a prévia. Agora, selecionar
uma espécie prepara sua ativação e a desativação das outras. Aplicar confirma
a troca; Descartar cancela. Uma cor padrão é selecionada se a espécie não
possuir nenhuma marcada. Abrir o painel e selecionar programaticamente o
pet continuam sem preparar alterações. Clicar novamente na mesma espécie
após descartar também permite preparar a troca.

22 testes passaram, incluindo troca real de Muuri por Clippy e cachorro,
cor padrão, substituição exclusiva, descarte e nova seleção. As preferências
reais da Muuri foram preservadas: Medium, movimento 1.19 e animação 1.31.
Arquivos corrigidos: deskpets/panel.py e tests/test_settings_panel.py.
Sem commit ou push. Reiniciar a instância anterior carrega esta correção.


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


## Ícone da Muuri

Adicionado deskpets/media/muuri/muuri.ico, convertido da primeira pose idle
original em nove resoluções de 16 a 256 px, com fundo transparente. Não houve
redesenho. O ícone original logo.ico foi preservado. Aplicativo, painel e
bandeja usam o novo ícone; o atalho Iniciar Muuri da Área de Trabalho e a cópia
em outputs foram atualizados. Validado carregamento dos três ícones no Qt e
os caminhos dos atalhos. Reinicie a instância antiga para atualizar a bandeja.


## Física opcional: gravidade e arremesso

O painel inclui “Ativar física”, salva por espécie em physics_enabled somente
quando Aplicar é pressionado. Ausência do campo equivale a desligado, preservando
o comportamento anterior. Nenhuma preferência real foi alterada nesta entrega.

Ligada, a física faz o pet cair até a base útil da tela, permite arremesso pela
velocidade recente do mouse, limita a velocidade e aplica colisões nas bordas,
um quique leve e desaceleração. Segurar novamente interrompe o arremesso.
Desligada, o pet permanece na altura em que é solto. A animação de arraste
existente acompanha o voo e a animação anterior retorna ao pousar.

A simulação usa o temporizador existente de interação, independente da velocidade
de animação. Aplicar preserva posição e orientação; mantém a velocidade apenas
quando a física continua habilitada. As cenas existentes de escalada permanecem
responsáveis pelo próprio movimento.

Validação: suíte de 33 testes aprovada, mais um teste adicional aprovado que
confirma movimento pelo temporizador com o painel oculto (34 testes no total).
Inclui gravidade, arremesso, colisões, repouso, arraste nativo, Aplicar/Descartar,
compatibilidade e assets. O launcher original também passou no teste de início.
Verificação de espaços e conflitos pelo git diff --check aprovada.
Sem commit ou push. Reinicie a instância anterior para carregar o código novo.


## Uma única instância pelo atalho

A entrada original deskpets.main:main agora verifica um mutex nomeado da sessão
do Windows antes de criar a aplicação, a bandeja ou os pets. Novas execuções
encerram imediatamente quando já existe uma instância. O Windows libera a
trava mesmo após encerramento forçado; não há arquivo de trava obsoleto.

Arquivos: deskpets/main.py, deskpets/single_instance.py e
tests/test_single_instance.py. Quatro testes passaram: cinco tentativas
consecutivas bloqueadas em processos separados, reinício após saída, liberação
após encerramento forçado, ausência de janelas duplicadas e saída normal.
É necessário encerrar uma vez as instâncias antigas, que ainda não têm a trava,
e iniciar novamente pelo atalho. Nenhuma configuração de pets foi alterada.
Sem commit ou push.
