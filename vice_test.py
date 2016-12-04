#!/usr/bin/env python3

from os import fork
from time import sleep
from socket import AF_INET, MSG_DONTWAIT, SOCK_STREAM, socket, timeout
from subprocess import DEVNULL, run
from sys import argv


def parse_address(addr):
    addr = addr.split(":")
    assert(len(addr) == 2)
    yield addr[0]
    yield int(addr[1])


def unprompt(output):
    output = output.split("\n")
    for i, line in enumerate(output):
        if line[0:4] == "(C:$" and line[8:10] == ") ":
            output[i] = line[10:].strip()
    return "\n".join(output)


class ViceClient:
    def __init__(self, host, port, timeout=1):
        self.host = host
        self.port = int(port)
        self.timeout = timeout
        self.sock = None
        self.cp = 0
        while not self.connect():
            self.sock.close()
            sleep(self.timeout)

    def connect_when_available(self):
        while True:
            try:
                self.sock.connect((self.host, self.port))
                return
            except ConnectionRefusedError:
                pass
            except ConnectionAbortedError:
                pass
            sleep(self.timeout)

    def connect(self):
        self.sock = socket(AF_INET, SOCK_STREAM)
        self.connect_when_available()
        self.sock.settimeout(self.timeout)
        self.command("m 0800 0807")
        self.check_cp()
        return not self.basic_empty() and \
            self.cp in (0xe5d1, 0xe5d4, 0xe5cd, 0xe5cf)

    def check_cp(self):
        regs = self.command("r").split("\n")
        if len(regs) == 3:
            self.cp = int(regs[1][2:6], 16)

    def basic_empty(self):
        return self.command("m 0801 0802")[9:14] == "00 00"

    def readall(self):
        ret = []
        try:
            ret.append(self.sock.recv(1024))
            while len(ret[-1]) > 0:
                ret.append(self.sock.recv(1024))
        except timeout:
            pass
        if len(ret) and not len(ret[-1]):
            ret.pop()
        return b"".join(ret)

    def command(self, cmd):
        cmd = "{}\n".format(cmd)
        #print(">", cmd)
        self.sock.sendall(cmd.encode())
        ret = unprompt(self.readall().decode())
        #print("<", len(ret), ret.replace("\n", "\\n"))
        return ret


def main():
    vice_cmd = [
        "x64", "-autoload", argv[1],
        "-remotemonitor", "-remotemonitoraddress", "localhost:9998"
    ]
    if fork() == 0:
        run(vice_cmd, universal_newlines=True, stdout=DEVNULL)
        return
    vc = ViceClient(*parse_address(vice_cmd[-1]))
    print(vc.command("d 080d 0819"))
    print(vc.command("d 0830 083b"))
    print(vc.command("m 0900 0907"))
    vc.command("quit")


if __name__ == "__main__":
    main()
