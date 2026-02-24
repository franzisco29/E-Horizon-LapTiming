from __future__ import annotations

import socket
from typing import Optional


def get_local_ipv4(prefer_prefixes: tuple[str, ...] = ("192.168.", "10.", "172.")) -> str:
    """
    VB: GetLocalIPAddress()
    In Python proviamo a trovare un IPv4 "LAN".
    """
    hostname = socket.gethostname()
    candidates: list[str] = []

    try:
        for info in socket.getaddrinfo(hostname, None):
            family, _, _, _, sockaddr = info
            if family == socket.AF_INET:
                ip = sockaddr[0]
                candidates.append(ip)
    except Exception:
        pass

    # Filtra preferenze (LAN più comune)
    for pref in prefer_prefixes:
        for ip in candidates:
            if ip.startswith(pref):
                return ip

    # fallback: tenta metodo "socket trick" senza connettersi davvero
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        pass

    return "IP non trovato"
