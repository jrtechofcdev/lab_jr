# JR Wi-Fi Lab CLI

Interface interativa em linha de comando para reduzir o trabalho manual de
copiar BSSID, canal e MAC entre `airodump-ng`, `aireplay-ng` e Wireshark.

O fluxo foi pensado para um roteador de teste próprio em laboratório. A
ferramenta **não contém quebra de senha**: não recebe wordlist, não executa
força bruta, não coleta PMKID e não chama nenhum modo de cracking.

## O que ela automatiza

1. Detecta as interfaces Wi-Fi e permite escolher por número.
2. Ativa modo monitor com `airmon-ng`.
3. Varre 2,4 GHz, 5 GHz ou ambas e converte o CSV do `airodump-ng` em uma
   tabela limpa.
4. Permite escolher o AP por número, sem copiar BSSID ou canal.
5. Exige registrar o BSSID em uma allowlist local de equipamentos autorizados.
6. Mantém uma captura direcionada ao AP escolhido.
7. Lista somente clientes observados como associados àquele BSSID.
8. Detecta quadros EAPOL e informa quais mensagens do four-way handshake foram
   vistas pelo `tshark`.
9. Abre o `.cap` no Wireshark, como usuário comum, com filtro de EAPOL e
   deauthentication já aplicado.

O modo recomendado é aguardar uma reconexão natural. Há uma ação ativa opcional
para solicitar a reautenticação de **um cliente selecionado**. Cada tentativa
executa somente uma rodada direcionada do `aireplay-ng`; a própria suíte pode
transmitir várias cópias dentro dessa rodada. São permitidas no máximo duas
tentativas por sessão, com intervalo mínimo de 30 segundos. Não existe alvo
broadcast, repetição contínua ou parâmetro para elevar esses limites.

## Requisitos

- Kali Linux ou Debian derivado;
- adaptador Wi-Fi com suporte a modo monitor;
- suporte a injeção apenas se a reautenticação controlada for usada;
- execução com `sudo` para alterar o modo da interface;
- ambiente gráfico para abrir o Wireshark automaticamente.

O instalador usa somente os pacotes oficiais do sistema:

- `aircrack-ng`
- `iw`
- `python3`
- `tshark`
- `wireshark` (opcional para interface gráfica)

## Instalação no Kali

Dentro desta pasta:

```bash
chmod +x install.sh jr-wifi-lab lib/airodump_csv.py
sudo ./install.sh
```

Para instalar somente o modo terminal, sem a GUI do Wireshark:

```bash
sudo ./install.sh --no-gui
```

O instalador não atualiza a distribuição e não executa a ferramenta. Ele apenas
instala pacotes ausentes e copia:

- executável para `/usr/local/bin/jr-wifi-lab`;
- parser para `/usr/local/lib/jr-wifi-lab/airodump_csv.py`;
- allowlist para `/etc/jr-wifi-lab/authorized_bssids`;
- capturas para `/var/lib/jr-wifi-lab/captures/`.

## Uso

Primeiro valide as dependências sem tocar na interface:

```bash
jr-wifi-lab --dry-run
```

Depois inicie o fluxo interativo:

```bash
sudo jr-wifi-lab
```

Uma execução com varredura maior e somente 2,4 GHz:

```bash
sudo jr-wifi-lab --scan-seconds 30 --band bg
```

`--authorized` substitui apenas a confirmação geral do início da sessão. Um
BSSID novo ainda exige a frase específica exibida na tela antes de qualquer
captura direcionada.

## Fluxo na tela

```text
Interfaces Wi-Fi
  1) wlan0           tipo=managed  phy=0

Redes WPA encontradas
  #   REDE                        BSSID             CAN  SINAL SEGURANCA CLIENTES
  1   ROTEADOR-LAB                AA:BB:CC:DD:EE:FF   6    -41 WPA2            1

Clientes associados a ROTEADOR-LAB
  #   CLIENTE             SINAL    PACOTES
  1   11:22:33:44:55:66     -38        124
```

Toda seleção é feita pelo número. BSSID, canal e MAC são passados aos comandos
como argumentos validados, sem `eval` e sem montar comandos em texto.

## Proteções implementadas

- confirmação explícita de uso autorizado;
- allowlist persistente de BSSIDs;
- segunda confirmação vinculada ao cliente para a ação ativa;
- reautenticação somente direcionada a um cliente e com limites fixos;
- nenhuma opção broadcast ou contínua;
- filtro de APs WPA e clientes realmente associados ao BSSID escolhido;
- validação de interface, canal, intervalos e caminhos;
- comandos executados por arrays/argumentos, sem `eval`;
- PIDs rastreados e encerrados por `SIGINT`/`SIGTERM`;
- restauração do modo da interface e de serviços pausados ao sair, inclusive com
  `Ctrl+C`;
- Wireshark nunca iniciado automaticamente como root;
- arquivos criados com permissões restritas e fora do repositório;
- logs da sessão sem credenciais ou conteúdo de wordlist.

Redes vizinhas continuarão visíveis na varredura porque o rádio as recebe. Isso
não as autoriza: só o BSSID explicitamente registrado pode seguir para captura
direcionada.

## Arquivos da sessão

Cada execução cria uma pasta isolada como:

```text
/var/lib/jr-wifi-lab/captures/session-AAAAMMDD-HHMMSS-XXXXXX/
```

Ela contém o CSV da varredura, o `.cap`, saídas do Aircrack-ng e `session.log`.
Se o programa foi aberto com `sudo` e o Wireshark é iniciado, somente o arquivo
de captura passa ao usuário original; logs e demais arquivos continuam
protegidos. Assim, a GUI nunca precisa ser executada como root.

Filtros úteis no Wireshark:

```text
eapol
```

```text
eapol || wlan.fc.type_subtype == 0x000c
```

## Testes de desenvolvimento

Os testes não ativam modo monitor nem enviam quadros:

```bash
./tests/run.sh
```

Eles verificam sintaxe Bash, ajuda, versão e parsing de snapshots do
`airodump-ng`, incluindo ESSID com vírgula.

## Encerramento seguro

Use a opção `0` do menu ou `Ctrl+C`. O trap de saída encerra apenas os processos
iniciados pela sessão, desativa a interface monitor criada pela ferramenta e
reinicia `NetworkManager`/`wpa_supplicant` apenas quando eles estavam ativos
antes do início.
