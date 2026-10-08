# Muuri 🐮

Uma vaquinha que vive no seu desktop.

<p><img src="deskpets/media/muuri/blue_idle_8fps.gif" alt="Muuri animada" width="160"></p>

Muuri é um desktop pet para Windows com animações, interação, arraste, física opcional e painel de configurações em português. É baseada no [DeskPets](https://github.com/Jumitti/DeskPets), mantendo Python/PyQt e os créditos da base original.

## ✨ Recursos

- Passeios pelo desktop, animações de descanso e reações.
- Arraste com o mouse e animação ao ser carregada.
- Física opcional com gravidade, arremesso e quique.
- Tamanhos e velocidades de movimento e animação independentes.
- Painel em português, seleção de outros pets e ícone na bandeja do Windows.
- Uma instância por sessão e preferências salvas entre execuções.

## 📦 Instalação

1. Abra [Releases](https://github.com/Felipx423/muuri/releases/latest).
2. Baixe **Muuri-Setup.exe**.
3. Execute o instalador e conclua a instalação.
4. Abra **Iniciar Muuri** pelo atalho ou pelo menu Iniciar.

Para **Windows 10/11 de 64 bits**. Não precisa de Python nem VS Code. O aplicativo ainda não possui assinatura digital própria. Para remover, use **Configurações do Windows → Aplicativos**; as preferências ficam preservadas.

## 🐮 Como usar

- Dê **quatro cliques rápidos** na Muuri para abrir o painel.
- Arraste com o mouse. Para gravidade e arremesso, marque **Ativar física** e clique em **Aplicar**.
- Ajuste tamanho, cores, velocidades, pet e camada no painel. A prévia não altera o pet até aplicar.
- Use o ícone na bandeja, perto do relógio, para abrir as configurações ou **Sair**.

## 🖼️ Screenshots

![Painel de configurações da Muuri](img/muuri-painel.png)

## 🛠️ Executar pelo código

No Windows, na raiz do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

## 🧪 Testes

Com o ambiente virtual ativado:

```powershell
python -m unittest discover -s tests -v
```

Ou use diretamente `.\.venv\Scripts\python.exe` no lugar de `python`.

## 📦 Build

Consulte [packaging/README.md](packaging/README.md) para compilar o executável e o instalador. O launcher continua sendo `run.py`. O [histórico de desenvolvimento](MUURI_INTEGRATION.md) registra etapas intermediárias, não instruções atuais.

## 📜 Créditos e licenças

- **DeskPets**, por **Minniti Julien (Jumitti)**: [repositório original](https://github.com/Jumitti/DeskPets). A licença MIT e seu aviso de copyright estão preservados em [LICENSE](LICENSE).
- **vscode-pets**, por **tonybaloney**: [projeto de inspiração da base](https://github.com/tonybaloney/vscode-pets). Os créditos e condições aplicáveis aos assets herdados continuam válidos.
- **Muuri**: design de referência fornecido pelo usuário; animações adaptadas para esta integração.
- **PyQt6**: a distribuição executável usa GPL v3 e inclui a licença, os fontes da aplicação e os assets necessários. As licenças das demais bibliotecas acompanham o instalador em `_internal/THIRD_PARTY_LICENSES`.

O ZIP de fonte incluído no instalador reutiliza os assets de `_internal/deskpets/media`. Após extrair o fonte, copie essa pasta para `deskpets/media` antes de compilar; o ZIP autônomo disponível nas versões já inclui os assets.

O pacote interno `deskpets`, o identificador do instalador, o mutex de instância única e a pasta instalada `MuuriDeskPets` permanecem por compatibilidade. Isso preserva imports, atualizações, preferências e a proteção contra instâncias duplicadas.
