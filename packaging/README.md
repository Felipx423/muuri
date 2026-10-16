# Compilar a distribuição Windows

Na raiz do projeto, com Python 3.12 de 64 bits:

    python -m venv .venv
    .venv\Scripts\python -m pip install -r requirements.txt pyinstaller==6.22.3
    .venv\Scripts\python packaging\build_windows.py

Use Inno Setup 6.7.3 para compilar packaging\muuri.iss com ISCC.exe.
O executável e arquivos de trabalho ficam em ../work/package; o instalador,
guia e código-fonte ficam em ../../outputs. Os diretórios são criados pelo builder.
A instalação é por usuário, sem administrador, com atalhos e desinstalador.
As preferências existentes são preservadas ao atualizar/reinstalar.
Os padrões de distribuição habilitam só a Muuri, Medium, velocidades 1x,
arraste ligado e física desligada, sem alterar as preferências do desenvolvedor.

O launcher original run.py continua sendo a entrada do executável. Assets,
Python, Qt e bibliotecas são incluídos pelo PyInstaller. O código-fonte completo
da adaptação acompanha a distribuição. As licenças das bibliotecas e a licença
MIT original são incluídas; o pacote com PyQt6 deve respeitar sua GPL v3.


O pacote usa hooks locais para os codecs de imagem necessários e para omitir
o renderizador PDF e o OpenGL de software: os widgets e a janela nativa do pet
usam pintura raster. O código-fonte incluído no instalador usa os assets já presentes em
_internal/deskpets/media, evitando duplicá-los dentro do ZIP. Após extrair o
fonte, copie essa pasta para deskpets/media antes de compilar. O ZIP autônomo
em outputs inclui também todos os assets e screenshots originais. Todas as
espécies, licenças e código Python são preservados. A compressão é LZMA2/ultra64.


## Identidade e compatibilidade

O pacote Windows usa a versão 1.3.0, nome Muuri, executável Muuri.exe,
instalador Muuri-Setup.exe e o ícone próprio existente. Nenhum publisher foi
inventado: o campo AppPublisher foi omitido. Os créditos continuam no guia,
no painel e na licença original. A versão 1.0.1 publicada não é substituída
automaticamente por uma compilação local.

O AppId do Inno Setup e DefaultDirName MuuriDeskPets são mantidos para atualizar
a instalação anterior sem criar outra entrada. O mutex PetlayerDeskPetsMuuri
é mantido para detectar também versões anteriores abertas. O pacote Python
deskpets e seu entry point original continuam compatíveis; esses nomes não
são a identidade visível do aplicativo. O AppUserModelID visível ao Windows
passa a Muuri; a integração com a barra de tarefas pode formar um novo grupo.

## Atualizações pelo aplicativo

O Windows instalado verifica a última release estável de Felipx423/muuri ao
iniciar e a cada seis horas. Também há uma ação na bandeja e em Preferências.
O download exige os assets Muuri-Setup.exe e MUURI-SHA256.txt, com linhas no
formato SHA-256 seguido de dois espaços e o nome do arquivo. Não publique
uma release como latest antes de enviar ambos os arquivos.

O instalador é baixado para o cache do usuário, validado por tamanho e SHA-256
e verificado novamente antes da execução. Um helper do PowerShell do Windows
aguarda o processo original sair, executa o Inno Setup na mesma pasta, sem
reiniciar o computador, e reabre Muuri.exe. Não há mudança na política de
execução do sistema. Em caso de falha, o helper informa o erro e mantém
update.log junto ao download para diagnóstico.

Mantenha AppId, DefaultDirName e as regras onlyifdoesntexist dos JSONs.
Atualize deskpets/version.py e AppVersion em muuri.iss a cada release do Muuri.
Execução por código-fonte não instala atualizações. No macOS, a ação abre
os downloads; a substituição automática do .app não faz parte desta versão.
