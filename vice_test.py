#!/usr/bin/env python3

from os import fork
from re import compile, MULTILINE
from time import sleep
from socket import AF_INET, MSG_DONTWAIT, SOCK_STREAM, socket, timeout
from subprocess import DEVNULL, run
from sys import argv

PROMPT_FILTER = compile("^\(C:\$[0-9a-fA-F]{4}\) ", flags=MULTILINE)


def parse_address(addr):
    addr = addr.split(":")
    assert(len(addr) == 2)
    yield addr[0]
    yield int(addr[1])


def connect_when_available(sock, addr, timeout):
    while True:
        try:
            sock.connect(addr)
            return
        except ConnectionRefusedError:
            pass
        except ConnectionAbortedError:
            pass
        sleep(timeout)


def readall(sock):
    ret = [sock.recv(1024)]
    try:
        while len(ret[-1]) > 0:
            ret.append(sock.recv(1024))
    except timeout:
        pass
    ret.pop()
    return b"".join(ret)


def filter_prompt(output):
    return PROMPT_FILTER.sub("", output)


def main():
    vice_cmd = [
        "x64", "-autoload", argv[1],
        "-remotemonitor", "-remotemonitoraddress", "localhost:9998"
    ]
    if fork() == 0:
        run(vice_cmd, universal_newlines=True, stdout=DEVNULL)
        return
    with socket(AF_INET, SOCK_STREAM) as sock:
        sock.settimeout(.5)
        connect_when_available(sock, tuple(parse_address(vice_cmd[-1])), .5)
        sock.sendall(b"d 080d 0819\n")
        print(filter_prompt(readall(sock).decode()))
        sock.sendall(b"d 0830 083b\n")
        print(filter_prompt(readall(sock).decode()))
        sock.sendall(b"m 0900 0908\n")
        print(filter_prompt(readall(sock).decode()))
        sock.sendall(b"quit\n")
        readall(sock).decode()


if __name__ == "__main__":
    main()
