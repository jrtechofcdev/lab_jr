#!/usr/bin/env python3
"""Parse airodump-ng CSV snapshots into shell-safe, deterministic records.

The airodump CSV format is only CSV-like: ESSIDs and probed names may contain
commas without being quoted.  This parser reconstructs those trailing fields
instead of asking the Bash front-end to split them unsafely.
"""

from __future__ import annotations

import argparse
import base64
import csv
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


MAC_RE = re.compile(r"^(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")


def clean(value: str) -> str:
    return value.strip().replace("\x00", "")


def normalized_mac(value: str) -> str:
    value = clean(value).upper()
    return value if MAC_RE.fullmatch(value) else ""


def integer(value: str, default: int = 0) -> int:
    try:
        return int(clean(value))
    except (TypeError, ValueError):
        return default


def encoded(value: str) -> str:
    return base64.b64encode(value.encode("utf-8", errors="replace")).decode("ascii")


@dataclass(frozen=True)
class AccessPoint:
    bssid: str
    channel: int
    power: int
    privacy: str
    cipher: str
    authentication: str
    essid: str


@dataclass(frozen=True)
class Station:
    mac: str
    power: int
    packets: int
    bssid: str
    probes: str


def parse(path: Path) -> tuple[list[AccessPoint], list[Station]]:
    aps: list[AccessPoint] = []
    stations: list[Station] = []
    section = "aps"

    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        for row in csv.reader(handle, skipinitialspace=False):
            if not row or not any(part.strip() for part in row):
                continue

            first = clean(row[0])
            if first == "BSSID":
                section = "aps"
                continue
            if first == "Station MAC":
                section = "stations"
                continue

            if section == "aps":
                # Fixed fields end at ID-length (index 12).  The final field is
                # Key; everything between them belongs to ESSID, including any
                # literal commas.
                if len(row) < 15:
                    continue
                bssid = normalized_mac(row[0])
                if not bssid:
                    continue
                essid = clean(",".join(row[13:-1]))
                aps.append(
                    AccessPoint(
                        bssid=bssid,
                        channel=integer(row[3]),
                        power=integer(row[8], -100),
                        privacy=clean(row[5]),
                        cipher=clean(row[6]),
                        authentication=clean(row[7]),
                        essid=essid,
                    )
                )
            else:
                if len(row) < 6:
                    continue
                mac = normalized_mac(row[0])
                bssid = normalized_mac(row[5])
                if not mac:
                    continue
                stations.append(
                    Station(
                        mac=mac,
                        power=integer(row[3], -100),
                        packets=integer(row[4]),
                        bssid=bssid,
                        probes=clean(",".join(row[6:])),
                    )
                )

    return aps, stations


def output_aps(aps: list[AccessPoint], stations: list[Station], secured_only: bool) -> None:
    client_counts = Counter(station.bssid for station in stations if station.bssid)
    rows = sorted(aps, key=lambda ap: (ap.power, ap.essid, ap.bssid), reverse=True)
    for ap in rows:
        if secured_only and "WPA" not in ap.privacy.upper():
            continue
        fields = (
            ap.bssid,
            str(ap.channel),
            str(ap.power),
            encoded(ap.privacy),
            encoded(ap.cipher),
            encoded(ap.authentication),
            str(client_counts[ap.bssid]),
            encoded(ap.essid),
        )
        print("|".join(fields))


def output_stations(stations: list[Station], bssid: str) -> None:
    target = normalized_mac(bssid)
    if not target:
        raise ValueError("BSSID invalido")
    rows = sorted(
        (station for station in stations if station.bssid == target),
        key=lambda station: (station.power, station.packets, station.mac),
        reverse=True,
    )
    for station in rows:
        fields = (
            station.mac,
            str(station.power),
            str(station.packets),
            encoded(station.probes),
        )
        print("|".join(fields))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_file", type=Path)
    subparsers = parser.add_subparsers(dest="command", required=True)

    aps = subparsers.add_parser("aps", help="Listar pontos de acesso")
    aps.add_argument("--secured-only", action="store_true")

    stations = subparsers.add_parser("stations", help="Listar clientes associados")
    stations.add_argument("--bssid", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.csv_file.is_file():
        print(f"arquivo nao encontrado: {args.csv_file}", file=sys.stderr)
        return 2

    try:
        aps, stations = parse(args.csv_file)
        if args.command == "aps":
            output_aps(aps, stations, args.secured_only)
        else:
            output_stations(stations, args.bssid)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
