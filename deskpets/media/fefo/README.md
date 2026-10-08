# Fefo

Referência visual canônica: `reference.svg`, fornecida pelo usuário. A pose raster `base.png` foi aprovada antes da produção das animações. O Fefo é uma ave verde com bico escuro, bochecha pêssego, pés cinza e penas roxas na asa e na cauda.

Os oito GIFs usam canvas transparente de **128 × 128 px**, com **8 frames** por ciclo. A duração alterna entre 120 e 130 ms, totalizando 1 segundo: o GIF limita os tempos a centésimos de segundo, então essa alternância representa a média de 8 fps. O engine aplica sua cadência de 8 fps e os multiplicadores existentes.

| Estado | Animação |
| --- | --- |
| idle | Respiração sutil e piscar |
| walk | Passos pequenos alternados |
| walk_fast | Trote com inclinação e passada mais marcada |
| run | Corrida com passada ampla e breves fases suspensas |
| swipe | Pequeno gesto da asa e inclinação da cabeça |
| lie | Descanso abaixado, pés recolhidos e piscar |
| drag | Suspenso, asas parcialmente abertas, pés soltos e balanço discreto |
| fly | Batidas de asas e breve planada, com pés recolhidos |

Todos os arquivos seguem `green_<estado>_8fps.gif`. A direção base é para a direita; o espelhamento fica a cargo do engine atual. `Original` mantém a altura de canvas de 128 px; outros tamanhos preservam a proporção. O personagem não ocupa todo o canvas.

Os estados foram gerados separadamente com a mesma referência aprovada. A preparação raster aplicou escala compartilhada por sequência, registro vertical, remoção de pequenos pontos isolados de alpha, paleta comum entre frames de cada GIF e transparência com índice reservado. Não usa chroma verde: corpo, cauda e penas permanecem opacos.

O cadastro inicial mantém Fefo desativado, tamanho Original, cor green, arraste permitido, quatro cliques para configurações, física desligada e multiplicadores em 1×. No painel, selecione **Fefo** e clique em **Aplicar**. Física, arraste, tamanhos, velocidades e persistência usam a infraestrutura genérica existente.

Para usar o voo, marque **Ativar física** e **Permitir arrastar com o mouse**, e clique em **Aplicar**. Enquanto segurado, o Fefo usa `drag`; após soltar no ar, usa `fly` e orienta-se pela velocidade horizontal. Ao pousar, retoma o estado terrestre anterior. Esses dois estados não entram no sorteio de ações no chão.

O perfil `physics` da espécie em `pets_data.json` define gravidade de 420 px/s² (padrão terrestre: 1800), resistência horizontal de 2,2 s⁻¹, resistência vertical de 1,2 s⁻¹ e queda limitada a 180 px/s. A velocidade horizontal reduz esse limite em até 45%, criando a planada. O arremesso conserva 85% da velocidade do mouse e acrescenta 180 px/s para cima quando há movimento. O pouso não quica. Não há voo autônomo infinito: o Fefo estabiliza o lançamento e desce suavemente.

As animações `drag` e `fly` foram refinadas a partir do Fefo existente e da mesma referência canônica, com registro do rosto e paleta compartilhada em cada ciclo. Os seis GIFs terrestres, `base.png` e `reference.svg` foram mantidos. O perfil é opcional; espécies sem perfil conservam a física anterior.

Nenhum asset, parâmetro ou comportamento da Muuri foi alterado para esta integração. A licença e os créditos do DeskPets permanecem preservados.
