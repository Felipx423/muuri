# Fefo

Referência visual canônica: `reference.svg`, fornecida pelo usuário. A pose raster `base.png` foi aprovada antes da produção das animações. O Fefo é uma ave verde com bico escuro, bochecha pêssego, pés cinza e penas roxas na asa e na cauda.

Os sete GIFs usam canvas transparente de **128 × 128 px**, com **8 frames** por ciclo. A duração alterna entre 120 e 130 ms, totalizando 1 segundo: o GIF limita os tempos a centésimos de segundo, então essa alternância representa a média de 8 fps. O engine aplica sua cadência de 8 fps e os multiplicadores existentes.

| Estado | Animação |
| --- | --- |
| idle | Respiração sutil e piscar |
| walk | Passos pequenos alternados |
| walk_fast | Trote com inclinação e passada mais marcada |
| run | Corrida com passada ampla e breves fases suspensas |
| swipe | Pequeno gesto da asa e inclinação da cabeça |
| lie | Descanso abaixado, pés recolhidos e piscar |
| drag | Suspenso, pés soltos e balanço discreto |

Todos os arquivos seguem `green_<estado>_8fps.gif`. A direção base é para a direita; o espelhamento fica a cargo do engine atual. `Original` mantém a altura de canvas de 128 px; outros tamanhos preservam a proporção. O personagem não ocupa todo o canvas.

Os estados foram gerados separadamente com a mesma referência aprovada. A preparação raster aplicou escala compartilhada por sequência, registro vertical, remoção de pequenos pontos isolados de alpha, paleta comum entre frames de cada GIF e transparência com índice reservado. Não usa chroma verde: corpo, cauda e penas permanecem opacos.

O cadastro inicial mantém Fefo desativado, tamanho Original, cor green, arraste permitido, quatro cliques para configurações, física desligada e multiplicadores em 1×. No painel, selecione **Fefo** e clique em **Aplicar**. Física, arraste, tamanhos, velocidades e persistência usam a infraestrutura genérica existente.

Nenhum asset, parâmetro ou comportamento da Muuri foi alterado para esta integração. A licença e os créditos do DeskPets permanecem preservados.
