# Eco

Referência visual canônica fornecida pelo usuário em `references/eco-canonical.png`.
O estilo suave em 3D, corpo verde-claro, rosto marfim sem boca, olhos azuis,
bochechas rosas, duas folhas e quatro membros verdes separados foram preservados.

## Animações

Todos os sete GIFs usam canvas transparente de **128 × 128 px**, oito frames,
loop infinito e ciclo de 1 segundo. O GIF alterna 120/130 ms entre frames para
representar a média de 8 fps sem erro acumulado de temporização do formato.
Os três ciclos de locomoção compartilham uma paleta; os quatro ciclos frontais
mantêm sua paleta original. Transparência no índice 255 e disposal 2 evitam
rastros. O personagem mantém margem em todos os frames.

- `idle`: movimento discreto, folhas e piscar.
- `walk`: passos alternados curtos, de perfil para a direita.
- `walk_fast`: de perfil, passos mais altos e balanço maior.
- `run`: de perfil, passada mais ampla e corpo inclinado para a frente.
- `swipe`: aceno com uma das mãos.
- `lie`: corpo abaixado, olhos fechados e respiração suave.
- `drag`: pose suspensa, mãos elevadas e pés oscilando.

A locomoção usa uma vista lateral virada para a direita; os demais estados
preservam a vista frontal da referência. O espelhamento horizontal continua
sendo feito pelo engine. Não há GIFs separados para esquerda/direita nem física
especial do Eco: ele usa os controles genéricos de arraste, física e velocidades.

## Produção e reprodução

A base foi preparada com a ferramenta integrada de geração de imagens. Após
falhas do serviço ao gerar os outros estados, o usuário autorizou animar a mesma
base por transformações de folhas, mãos e pés. Nenhum frame redesenha o Eco.
O atlas de idle inicialmente gerado foi substituído pelo mesmo processo para
evitar mudanças de identidade entre estados. Não há placeholders nos GIFs.

`source/master.png` preserva a base de produção. `source/animate.py` contém o
processo determinístico em Pillow: extração das partes existentes, limpeza de
ruído do alpha, registro comum, transformações e conversão para GIF.
`source/sideways.py`, chamado automaticamente, projeta a textura do corpo
original sobre um volume arredondado girado para a direita e anima a passada
lateral, com apoio do pé indo para trás e balanço para a frente. Folhas, mãos
e pés vêm da mesma base. O pé mais distante pode ficar parcialmente oculto
pelo pé próximo; as mãos continuam separadas do corpo por transparência.
Não existe código de projeção executado pelo aplicativo: ele lê os GIFs prontos.
Para reproduzir a
partir da raiz do projeto, sem sobrescrever os assets usados pelo aplicativo:

```powershell
.\.venv\Scripts\python.exe deskpets/media/eco/source/animate.py --output build/eco-assets
```

`manifest.json` registra os bounds dos 56 frames. `base.png` é a prévia de 128 px.
As preferências pessoais em `pets_list.json` não foram alteradas: o painel
descobre o Eco pelo catálogo, e salva sua entrada ao adicioná-lo e aplicar.
Os builds também geram sua entrada padrão automaticamente, inicialmente inativa.
