# Friguinho

Friguinho é um pinguim azul-marinho com rosto e barriga brancos, olhos azuis,
bico e pés alaranjados e bochechas rosadas. A referência canônica enviada pelo
usuário está em `references/friguinho-canonical.png`; `source/master.png` é a
base transparente preparada para o pet.

## Animações

Os sete estados usam canvas transparente de 128 × 128 px, oito frames e loop
infinito. Idle, walk, walk_fast e run derivam da mesma base: os pés são separados
por cor e movidos em ciclos curtos, enquanto o corpo acompanha a passada.
Swipe, lie e drag usam poses derivadas da mesma base canônica, com pequenas
transformações entre frames. O espelhamento esquerda/direita continua sendo
feito pelo engine.

Para reproduzir os GIFs a partir da raiz do projeto:

```powershell
.\.venv\Scripts\python.exe deskpets/media/friguinho/source/animate.py
```

O processo gera os GIFs, `base.png`, `source/manifest.json` e a folha de revisão
`source/all-frames.png`. Não há lógica especial do Friguinho no engine.
