#!/usr/bin/env python3
#
# Copyright (c) 2016, mar77i <mar77i at mar77i dot ch>
#
# This software may be modified and distributed under the terms
# of the ISC license.  See the LICENSE file for details.

from argparse import ArgumentParser
from opcodes import OPCODES, is_illegal
from sys import stderr

lo = lambda x: x & 0xff
hi = lambda x: (x >> 8) & 0xff


class MOS6502Parser:
    comment_chars = (";", )
    opcodes = dict()

    @classmethod
    def setup(cls):
        for op in OPCODES:
            assert(op.mnemonic not in cls.opcodes)
            cls.opcodes[op.mnemonic] = op.modes
            for alias in op.alias:
                assert(alias not in cls.opcodes)
                cls.opcodes[alias] = op.modes

    def block_add(self, *args):
        if len(self.blocks) == 0:
            self.blocks.append({
                "data": bytearray(),
            })
        for arg in args:
            self.blocks[-1]["data"].append(arg)

    def __init__(self, infh):
        self.blocks = []
        self.labels = {}
        self.forward_labels = {}
        self.parse_offset = 0
        for line in infh.readlines():
            for cc in self.comment_chars:
                comment = line.find(cc)
                if comment >= 0:
                    line = line[:comment]
            colon = line.find(":")
            if colon >= 0:
                # todo: remove label from beginning of line
                label, line = line.split(":", 1)
                label = label.strip()
                self.labels[label] = len(self.blocks[-1]["data"])
                if label in self.forward_labels:
                    forward_labels = self.forward_labels.pop(label)
                    for b, pos in forward_labels:
                        self.blocks[b]["data"][pos + 1] = \
                            len(self.blocks[b]["data"]) - pos - 2
            line = line.split()
            if len(line) > 0:
                self.interpret(line)

    def interpret(self, line):
        if line[0].upper().startswith(".ORG"):
            assert(len(line) == 2)
            self.blocks.append({
                "org": self.parse_num(line[1]),
                "data": bytearray(),
            })
            return
        elif line[0].upper().startswith(".HEX"):
            for x in line[1:]:
                num = int(x[-4:], 16)
                if len(x) > 2:
                    self.block_add(lo(num))
                    num >>= 8
                self.block_add(num)
            return
        assert(len(line) in (1, 2))
        self.parse_offset = len(self.blocks[-1]["data"])
        for mn, op in self.opcodes.items():
            if line[0].upper().startswith(mn):
                data = self.parse_op(op, line[1] if len(line) > 1 else None)
                self.block_add(*data)
                return

    def parse_op(self, op, arg):
        if arg is None:
            return self.op_match(op, "_", "a"),
        elif arg.upper() == "A":
            return self.op_match(op, "a"),
        elif arg[0] == "#":
            return self.op_match(op, "#"), self.parse_num(arg[1:])
        elif arg[0] == "(" and arg[-3:].upper() == ",X)":
            return (self.op_match(op, "iz,x"), self.parse_num(arg[1:-3]))
        elif arg[0] == "(" and arg[-3:].upper() == "),Y":
            return (self.op_match(op, "iz,y"), self.parse_num(arg[1:-3]))
        elif arg[0] == "(" and arg[-1].upper() == ")":
            return (self.op_match(op, "ind"), self.parse_num(arg[1:-1]))
        elif arg[-2:].upper() == ",X":
            return self.op_by_argwidth(arg[:-2], op, "zp,x", "abs,x")
        elif arg[-2:].upper() == ",Y":
            return self.op_by_argwidth(arg[:-2], op, "zp,y", "abs,y")
        if "r" in op:
            return op["r"], self.relative(arg)
        return self.op_by_argwidth(arg, op, "zp", "abs")

    @staticmethod
    def parse_num(arg, return_use_wide=False):
        use_wide = False
        num = None
        if arg[0] == "$":
            arg = arg[1:]
            if len(arg) > 2:
                use_wide = True
            num = int(arg, 16)
        elif arg is not None:
            if arg[0] == "0" and len(arg) > 1:
                use_wide = True
            num = int(arg)
        if return_use_wide:
            return use_wide, num
        return num

    @staticmethod
    def op_match(op, *args):
        for x in args:
            if x in op:
                x = op[x]
                return x[0] if type(x) is list else x
        raise ValueError("No such mode {} in {}".format(str(op), str(args)))

    @classmethod
    def op_by_argwidth(cls, arg, op, shortmode, longmode):
        use_wide, num = cls.parse_num(arg, True)
        if shortmode in op and not (use_wide and longmode in op):
            return self.op_match(op, shortmode), num
        return cls.op_match(op, longmode), lo(num), hi(num)

    def relative(self, arg):
        jtgt = 0
        if arg in self.labels:
            jtgt = self.labels[arg] - self.parse_offset
        else:
            try:
                jtgt = self.blocks[-1].get("org", 0) + self.parse_num(arg)
            except ValueError:
                jtgt = 2
                if arg not in self.forward_labels:
                    self.forward_labels[arg] = []
                self.forward_labels[arg].append((
                    len(self.blocks) - 1,
                    self.parse_offset,
                ))
        return lo(jtgt - 2)

    def write(self, fh):
        org = None
        offset = 0
        # every block but the first must start at a known address
        # - only .org <address> starts a block
        for block in self.blocks:
            if "org" in block:
                block["org"] = block["org"] & 0xffff
                if org is None:
                    org = block["org"] - offset
            offset += len(block["data"])
        current = 0
        if org is not None:
            self.blocks[0]["org"] = org
            fh.write(bytes(bytearray((lo(org), hi(org)))))
            current = org
        self.blocks = sorted(self.blocks, key=lambda block: block["org"])
        for i, block in enumerate(self.blocks):
            assert(self.blocks[i]["org"] >= current)
            # add padding between blocks
            if self.blocks[i]["org"] > current:
                fh.write(b"\0" * (self.blocks[i]["org"] - current))
            fh.write(block["data"])
            current += len(block["data"])


def main():
    MOS6502Parser.setup()
    ap = ArgumentParser(description="simple 6502 Assembler")
    ap.add_argument("--output", "-o", default="a.prg", help="output file")
    ap.add_argument("input", metavar="FILE", type=str, nargs=1)
    args = ap.parse_args()
    with open(args.input[0], "r") as infh:
        parser = MOS6502Parser(infh)
    with open(args.output, "wb") as outfh:
        parser.write(outfh)


if __name__ == "__main__":
    main()
