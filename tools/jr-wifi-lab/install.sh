#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
ASSUME_YES=0
INSTALL_GUI=1

usage() {
    cat <<'EOF'
Instalador do JR Wi-Fi Lab para Kali/Debian

Uso:
  sudo ./install.sh [--yes] [--no-gui]

  --yes       nao pede confirmacao para instalar pacotes ausentes
  --no-gui    instala tshark, mas nao instala a interface grafica Wireshark
EOF
}

while (($#)); do
    case "$1" in
        --yes) ASSUME_YES=1 ;;
        --no-gui) INSTALL_GUI=0 ;;
        -h|--help) usage; exit 0 ;;
        *) printf 'Opcao desconhecida: %s\n' "$1" >&2; exit 2 ;;
    esac
    shift
done

(( EUID == 0 )) || {
    printf 'Execute com sudo: sudo %s\n' "$0" >&2
    exit 1
}

[[ -f "$SCRIPT_DIR/jr-wifi-lab" && -f "$SCRIPT_DIR/lib/airodump_csv.py" ]] || {
    printf 'Arquivos da ferramenta incompletos em %s\n' "$SCRIPT_DIR" >&2
    exit 1
}

command -v apt-get >/dev/null 2>&1 || {
    printf 'Este instalador requer apt-get (Kali ou Debian).\n' >&2
    exit 1
}

packages=(aircrack-ng iw python3 coreutils tshark)
(( INSTALL_GUI )) && packages+=(wireshark)
missing_packages=()
for package in "${packages[@]}"; do
    dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q 'install ok installed' \
        || missing_packages+=("$package")
done

if ((${#missing_packages[@]})); then
    printf 'Pacotes ausentes: %s\n' "${missing_packages[*]}"
    if (( ! ASSUME_YES )); then
        read -r -p 'Instalar agora com apt-get? [s/N]: ' answer
        [[ "${answer,,}" == "s" || "${answer,,}" == "sim" ]] || {
            printf 'Instalacao cancelada sem alterar pacotes.\n'
            exit 0
        }
    fi
    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${missing_packages[@]}"
fi

install -d -m 0755 /usr/local/lib/jr-wifi-lab
install -d -m 0750 /etc/jr-wifi-lab /var/lib/jr-wifi-lab/captures
install -m 0755 "$SCRIPT_DIR/jr-wifi-lab" /usr/local/bin/jr-wifi-lab
install -m 0755 "$SCRIPT_DIR/lib/airodump_csv.py" /usr/local/lib/jr-wifi-lab/airodump_csv.py
[[ -e /etc/jr-wifi-lab/authorized_bssids ]] \
    || install -m 0600 /dev/null /etc/jr-wifi-lab/authorized_bssids

printf '\nJR Wi-Fi Lab instalado.\n'
printf 'Valide: jr-wifi-lab --dry-run\n'
printf 'Execute: sudo jr-wifi-lab\n'
