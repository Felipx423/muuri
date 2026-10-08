# Cato

Referências visuais canônicas fornecidas no ZIP Projeto ACTA:

- references/acta-head-fish.png: rosto, três listras na testa, orelhas, focinho, bigodes e espinha de peixe turquesa.
- references/acta-seated-fish.png: proporção do corpo, peito/barriga bege, patas pequenas, cauda longa curva e relação com o peixe.
- references/acta-peek.png: olhos grandes azul-escuros, brilho e expressão arteira.

As três referências foram analisadas em conjunto. A base raster preserva a identidade e adapta a pose para caminhar em quatro patas. O halo branco externo dos stickers e os sinais decorativos não foram incorporados aos GIFs. A anatomia bege permanece opaca. Não há roupas ou objetos novos.

## Assets

Os sete GIFs usam canvas transparente de 128 × 128 px, oito frames e direção base para a direita. Original mantém os 128 px do canvas. Há espaço transparente para as orelhas, cauda, bigodes, patas e peixe; os contatos de apoio ficam próximos da mesma baseline. O engine existente espelha os frames.

| Estado | Ciclo |
| --- | --- |
| idle | Respiração discreta, piscada, leve movimento da cauda, espinha turquesa na boca |
| walk | Passada alternada sobre quatro patas |
| walk_fast | Trote com passada maior e fase suspensa |
| run | Corrida com recolhimento e extensão das patas |
| swipe | Percebe, pega, mordisca/abraça a espinha turquesa e devolve ao chão |
| lie | Descanso abaixado com respiração, olhos sonolentos e espinha turquesa nas patas |
| drag | Corpo suspenso, quatro patas soltas, orelhas e cauda reagindo |

Cada estado foi gerado separadamente a partir da mesma base. A primeira caminhada foi descartada por uma pata dianteira quase estática; somente esse ciclo foi refeito. A preparação mantém uma escala compartilhada, registra as poses no canvas, preserva movimentos entre frames e usa uma paleta comum aos sete GIFs. A transparência usa índice reservado, sem remoção de cores do personagem. A duração alterna 120/130 ms, totalizando um segundo por ciclo (média de 8 fps); o engine mantém sua cadência e os multiplicadores.

Na revisão da espinha de peixe, apenas idle e lie foram editados a partir dos respectivos atlases existentes. O peixe aparece nesses dois ciclos e no swipe; caminhada, trote, corrida e arraste permanecem iguais. A revisão reutiliza a paleta existente e mantém canvas, escala de produção e duração dos ciclos.

## Integração

Cato é cadastrado como espécie cato, cor orange, inicialmente desativado, tamanho Original, arraste permitido, quatro cliques para o painel, física desligada e multiplicadores em 1×. Os parâmetros terrestres de movimento usam passos de 4/8/12 pixels para caminhada/trote/corrida, ajustados à base maior. Os controles existentes continuam independentes.

Selecione Cato no painel e clique em Aplicar. Para queda e arremesso, marque Ativar física e aplique. Cato não define perfil physics: herda a gravidade, o atrito e o quique terrestres padrão. Enquanto arrastado ou lançado no ar usa drag; no pouso retoma o estado terrestre anterior. Não recebe fly, planada ou impulso de asas do Fefo.

## Peek

A referência de Cato espiando foi preservada. O cadastro aceita nomes de estados adicionais, mas o engine atual não possui um modo de se esconder atrás de uma borda da tela. Um GIF recortado dentro da janela seria apenas uma imitação dessa interação e não garantiria posicionamento na borda. Peek fica como funcionalidade futura; não há GIF ou alteração de engine para ele nesta entrega.

## Créditos

Cato e as imagens de referência: Projeto ACTA, fornecidas pelo usuário. Base e animações raster produzidas/adaptadas a partir dessas referências. Licença MIT e créditos originais do DeskPets permanecem nos arquivos originais. Nenhum asset ou parâmetro da Muuri, Fefo ou demais pets foi alterado para adicionar Cato.
