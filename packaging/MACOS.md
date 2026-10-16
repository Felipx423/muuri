# Muuri para macOS — Apple Silicon

Esta implementação mantém Python/PyQt, os GIFs/JSONs, os perfis de física e o suporte Windows. O alvo inicial é arm64 (M1 ou posterior), com macOS 13+. O build verifica a arquitetura e as versões mínimas gravadas nas bibliotecas: se uma dependência exigir um macOS posterior, o pacote é recusado em vez de anunciar compatibilidade incorreta.

O `.app` precisa ser compilado no macOS. Preparar os fontes em Windows não produz um aplicativo Mac e não substitui a validação de Cocoa/Spaces/Retina no dispositivo.

## Gerar o primeiro aplicativo

Em um Mac Apple Silicon, use Python 3.12 de https://www.python.org/downloads/macos/ e as ferramentas de linha de comando da Apple. O Terminal deve estar rodando nativamente em arm64, fora do Rosetta. Na raiz do projeto:

```bash
bash packaging/BUILD-MACOS.command
```

O script cria `.venv` local, instala as dependências de build, executa os testes e gera o aplicativo e o DMG. Alternativamente:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r packaging/requirements-macos.txt
.venv/bin/python packaging/run_tests.py
.venv/bin/python packaging/build_macos.py --dmg
```

Saídas, relativas à raiz do projeto:

- `build/macos/dist/Muuri.app`: aplicativo completo.
- `dist/macos/Muuri-macOS-arm64.zip`: aplicativo compactado com metadados/symlinks preservados pelo `ditto`.
- `dist/macos/Muuri-macOS-arm64.dmg`: imagem com aplicativo e atalho para Applications.
- `dist/macos/Muuri-macOS-codigo-fonte.zip`: fonte completo com assets e preferências padrão, sem preferências pessoais.
- `dist/macos/MUURI-macOS-SHA256.txt`: hashes dos arquivos finais.

Para executar pelo código, após instalar as dependências:

```bash
.venv/bin/python run.py
```

## Usar o aplicativo

Abra o DMG, arraste `Muuri.app` para Applications e abra o aplicativo pelo Finder. Quem recebe o `.app` não precisa instalar Python.

O ícone da Muuri aparece na barra de menus, com **Abrir configurações**, **Atualizar pets** e **Sair**. O aplicativo fica residente nessa barra, sem exigir uma janela do painel aberta. Fechar o painel mantém os pets ativos. Quatro cliques rápidos em Muuri, Fefo, Cato ou Manu também abrem as configurações. No macOS, use as ações do menu do ícone; o menu nativo abre ao clicar, e o gesto de duplo clique do ícone não é a forma principal de abertura.

Ative quantas espécies quiser, ajuste **Quantidade** para criar cópias e confirme em **Aplicar**. Tamanho, velocidades, arraste e física continuam por espécie. Fefo mantém seu perfil aéreo.

Preferências ficam em `~/Library/Application Support/Muuri/`, fora de `Muuri.app`; atualizações do aplicativo preservam os arquivos existentes e os campos desconhecidos. A pasta `locks/` impede outra instância do aplicativo, sem limitar a quantidade de pets da instância ativa. Desenvolvedores/testes podem usar `MUURI_CONFIG_DIR` para uma pasta separada.

O cálculo da área útil usa a tela principal em coordenadas lógicas do Qt, excluindo Dock e barra de menus. O Cocoa mantém os pets visíveis quando outro aplicativo está ativo. Os pets são configurados para acompanhar os desktops comuns, sem pedir o papel de janela auxiliar sobre apps em tela cheia. Spaces, Stage Manager, mudança de monitor, escala Retina e Dock ocultável precisam de validação visual no Mac antes de declarar paridade completa.

## Assinatura e distribuição

O primeiro build recebe assinatura ad hoc, necessária para os binários arm64. Isso não é uma assinatura Developer ID e não significa que o aplicativo foi notarizado. Um download de teste pode ser bloqueado pelo Gatekeeper; use apenas um pacote cuja origem você confia e siga o fluxo de **Ajustes do Sistema → Privacidade e Segurança → Abrir Mesmo Assim**, quando disponível. Não é necessário desativar a segurança do sistema.

Para uma distribuição pública com Developer ID, depois de instalar o certificado na máquina de build:

```bash
.venv/bin/python packaging/build_macos.py --dmg --codesign-identity "Developer ID Application: NOME (TEAMID)"
```

O builder assina os componentes com a identidade escolhida, ativa hardened runtime e verifica a assinatura final. A notarização é uma etapa adicional, usando credenciais guardadas no Keychain pelo `notarytool`; não coloque certificados, senhas ou chaves no repositório. Exemplo após configurar um perfil local chamado `MUURI_NOTARY`:

```bash
xcrun notarytool submit dist/macos/Muuri-macOS-arm64.dmg --keychain-profile MUURI_NOTARY --wait
xcrun stapler staple dist/macos/Muuri-macOS-arm64.dmg
xcrun stapler validate dist/macos/Muuri-macOS-arm64.dmg
```

Após notarização/staple, recalcule os hashes do DMG alterado antes de publicar. O workflow `.github/workflows/build-macos.yml` prepara um candidato ad hoc no runner Apple Silicon. Releases estáveis usam `.github/workflows/release.yml`: ao enviar uma tag `muuri-v*`, ele testa e compila Windows e macOS e publica os dois pacotes juntos.

## Validação

`packaging/run_tests.py` usa preferências temporárias para que as velocidades pessoais não interfiram nos testes. Os testes de mensagens Win32 são específicos do Windows e ficam pulados no Mac; os testes Qt cobrem seu equivalente, além dos testes compartilhados de física, GIFs, quantidades e persistência. Os testes Cocoa e de importação sem Win32 só rodam em macOS. Testar a implementação Qt em Windows não valida os detalhes nativos do Mac.

O builder verifica arquitetura arm64, assinatura, metadados, versões mínimas de bibliotecas, licenças, fontes, defaults e hashes de todos os assets. Depois, inicia o executável com configurações temporárias e sem Python no PATH, e confere que outras execuções encerram sem duplicar o aplicativo. Esse teste de início não substitui a inspeção visual dos pets.

Ao gerar o DMG, também monta a imagem em modo somente leitura, copia `Muuri.app` para uma pasta de instalação temporária, desmonta o volume e verifica a assinatura e a inicialização da cópia instalada. Isso confirma que o aplicativo não depende do volume montado ou da pasta de compilação.

Checklist visual no Mac: todos os pets e estados; transparência e espelhamento; arraste/arremesso e voo do Fefo; quatro cliques com/sem arraste; várias espécies e cópias; Aplicar/Descartar/reinício; frente/atrás das janelas; barra de menus/Sair; Retina, Dock, Spaces, tela cheia e monitores. Anote versão do macOS e modelo do Mac.

## Créditos e fontes

DeskPets por Minniti Julien (Jumitti), licença MIT preservada em `LICENSE`, e créditos dos assets originais de vscode-pets continuam incluídos. Muuri, Fefo, Cato e Manu usam suas referências existentes, sem regeneração nesta adaptação.

O aplicativo inclui as licenças das bibliotecas em `Contents/Resources/THIRD_PARTY_LICENSES` e os fontes da aplicação em `Contents/Resources/Muuri-codigo-fonte.zip`. Esse ZIP interno reutiliza os assets de `Contents/Resources/deskpets/media`; o ZIP autônomo contém tudo. A distribuição com PyQt6 continua sujeita à licença GPL v3 dessa biblioteca.

Referências técnicas: https://doc.qt.io/qt-6.11/macos.html · https://pyinstaller.org/en/stable/usage.html · https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution
