# Atualizações do Muuri

No Windows, instale o Muuri 1.4.3 ou posterior uma vez. Depois, quando
aparecer uma nova versão na bandeja, clique no aviso e em **Atualizar agora**.
O aplicativo baixa o instalador, confirma a origem, o tamanho e o SHA-256,
fecha antes da substituição e abre novamente somente depois de confirmar a
versão instalada. Seus pets, tamanhos, velocidades e demais preferências são
preservados.

Também é possível procurar uma versão em **Preferências → Atualizações**
ou em **Verificar atualizações** no menu da bandeja. É possível escolher
**Mais tarde** e continuar usando os pets normalmente.

A verificação ocorre ao abrir e a cada seis horas. Sem internet, o aplicativo
continua funcionando. Os quatro artefatos da release estável (instalador e
manifesto Windows, DMG e manifesto macOS) precisam estar publicados na release
oficial de [Felipx423/muuri](https://github.com/Felipx423/muuri/releases). O
instalador ou DMG da plataforma é conferido por tamanho e SHA-256 antes de
ser usado. O computador não é reiniciado.

No macOS Apple Silicon, **Preferências → Atualizações** baixa e verifica
`Muuri-macOS-arm64.dmg` usando `MUURI-macOS-SHA256.txt` e abre a imagem no
Finder. Arraste `Muuri.app` para `Applications` e substitua a cópia existente;
as preferências em `~/Library/Application Support/Muuri/` permanecem intactas.
O app não notarizado pode exigir **Privacidade e Segurança → Abrir Mesmo
Assim** na primeira abertura.

As versões anteriores a 1.2.0 não possuem o atualizador. Na execução pelo
código-fonte, a ação continua direcionando para os downloads, sem substituir o
projeto em execução.
