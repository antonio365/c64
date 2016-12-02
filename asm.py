#!/usr/bin/env python3
#
# Copyright (c) 2016, mar77i <mar77i at mar77i dot ch>
#
# This software may be modified and distributed under the terms
# of the ISC license.  See the LICENSE file for details.

from argparse import ArgumentParser, FileType
from functools import partial
from opcodes import first_mode, INSTRUCTION_LENGTH, is_illegal, OPCODES
from sys import stderr

lo = lambda x: x & 0xff
hi = lambda x: (x >> 8) & 0xff

warn = partial(print, file=stderr)


def parse_num(arg, return_use_long=False):
    use_long = False
    num = None
    if arg[0] == "$":
        arg = arg[1:]
        if len(arg) > 2:
            use_long = True
        num = int(arg, 16)
    else:
        if arg[0] == "0" and len(arg) > 1:
            use_long = True
        num = int(arg)
    if return_use_long:
        return use_long, num
    return num


class Instruction:
    def __init__(self, parser, mnemonic, opcode, arg):
        self.parser = parser
        self.opcode = opcode
        dot = mnemonic.find(".")
        self.mnemonic = (mnemonic if dot < 0 else mnemonic[:dot]).upper()
        assert(self.mnemonic == opcode.mnemonic)
        self.mode = mnemonic[dot + 1:] if dot >= 0 else None
        self.arg = arg
        self.num = None
        self.inst = None
        self.len = 1

    def parse_mode(self):
        if self.arg is None:
            if "a" in self.opcode.modes:
                return "a"
            return "_"
        if self.arg.upper() is "A":
            return "a"
        if self.arg[0] == "#":
            self.arg = self.arg[1:]
            return "#"
        if "r" in self.opcode.modes:
            return "r"
        if self.arg[0] == "(" and self.arg[-3:].upper() == ",X)":
            self.arg = self.arg[1:-3]
            return "zi,x"
        if self.arg[0] == "(" and self.arg[-3:].upper() == "),Y":
            self.arg = self.arg[1:-3]
            return "zi,y"
        if self.arg[0] == "(" and self.arg[-1] == ")":
            self.arg = self.arg[1:-1]
            return "ind"
        pair = ["zp", "abs"]
        if self.arg[-2:].upper() == ",X":
            self.arg = self.arg[:-2]
            pair = ["zp,x", "abs,x"]
        elif self.arg[-2:].upper() == ",Y":
            self.arg = self.arg[:-2]
            pair = ["zp,y", "abs,y"]
        for i in range(len(pair) - 1, -1, -1):
            if pair[i] not in self.opcode.modes:
                pair.pop(i)
        assert(len(pair) > 0)
        use_long, self.num = self.parse_num_or_label(True)
        return pair[-1 if use_long else 0]

    def adjust(self):
        if self.len == 1:
            return self.inst,
        if self.len == 2:
            return self.inst, self.num
        elif self.len == 3:
            return self.inst, lo(self.num), hi(self.num)
        raise ValueError("{}".format(self.mnemonic))

    def parse(self):
        if self.mode is None:
            self.mode = self.parse_mode()
            assert(self.mode in self.opcode.modes)
        self.len = INSTRUCTION_LENGTH[self.mode]
        if self.inst is None:
            self.inst = first_mode(self.opcode, self.mode)
        if self.mode == "r":
            return self.inst, self.relative()
        if self.len > 1 and self.num is None:
            self.num = self.parse_num_or_label()
        return self.adjust()

    def parse_num_or_label(self, return_use_long=False):
        use_long = False
        num = None
        label = self.parser.labels.get(self.arg, None)
        if label is not None:
            num = self.parser.blocks[-1].get("org", 0) + label
        else:
            try:
                use_long, num = parse_num(self.arg, True)
            except ValueError:
                num = 0
                use_long = True
                if self.arg not in self.parser.forward_labels:
                    self.parser.forward_labels[self.arg] = []
                self.parser.forward_labels[self.arg].append({
                    "block": len(self.parser.blocks) - 1,
                    "offset": self.parser.offset,
                    "mode": "abs",
                })
        if return_use_long:
            return use_long, num
        return num


    def relative(self):
        j = -2
        if self.arg in self.parser.labels:
            j += self.parser.labels[self.arg] - self.parser.offset
        else:
            try:
                j += self.parser.blocks[-1].get("org", 0) + parse_num(self.arg)
            except ValueError:
                j += 2
                if self.arg not in self.parser.forward_labels:
                    self.parser.forward_labels[self.arg] = []
                self.parser.forward_labels[self.arg].append({
                    "block": len(self.parser.blocks) - 1,
                    "offset": self.parser.offset,
                    "mode": "r",
                })
        assert(j > -129 and j < 128)
        return lo(j)


    def __str__(self):
        return "<Instruction({})>".format(str({
            "opcode": self.opcode,
            "mnemonic": self.mnemonic,
            "mode": self.mode,
            "arg": self.arg,
            "num": self.num,
            "inst": self.inst,
            "len": self.len,
        }))


class MOS6502Parser:
    comment_chars = (";", )

    def block_add(self, *args):
        if len(self.blocks) == 0:
            self.blocks.append({
                "data": bytearray(),
            })
        for arg in args:
            self.blocks[-1]["data"].append(arg)

    def __init__(self, infh, warn_illegal):
        self.warn_illegal = warn_illegal
        self.blocks = []
        self.labels = {}
        self.forward_labels = {}
        self.offset = 0
        for line in infh.readlines():
            for cc in self.comment_chars:
                comment = line.find(cc)
                if comment >= 0:
                    line = line[:comment]
            self.offset = len(self.blocks[-1]["data"]) \
                if len(self.blocks) else 0
            colon = line.find(":")
            if colon >= 0:
                # todo: remove label from beginning of line
                label, line = line.split(":", 1)
                label = label.strip()
                self.labels[label] = len(self.blocks[-1]["data"])
                if label in self.forward_labels:
                    self.insert_forward_label(self.forward_labels.pop(label))
            line = line.split()
            if len(line) > 0:
                self.interpret(line)
        assert(len(self.forward_labels) == 0)

    def insert_forward_label(self, forward_labels):
        for fwl in forward_labels:
            data = self.blocks[fwl["block"]]["data"]
            if fwl["mode"] == "r":
                data[fwl["offset"] + 1] = len(data) - fwl["offset"] - 2
            elif fwl["mode"] == "abs":
                addr = self.blocks[fwl["block"]].get("org", 0) + len(data)
                data[fwl["offset"] + 1] = lo(addr)
                data[fwl["offset"] + 2] = hi(addr)

    def interpret(self, line):
        if line[0].upper().startswith(".ORG"):
            assert(len(line) == 2)
            self.blocks.append({
                "org": parse_num(line[1]),
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
        for op in OPCODES:
            if line[0].upper().startswith(op.mnemonic):
                inst = Instruction(
                    self, line[0], op, line[1] if len(line) > 1 else None
                )
                inst = inst.parse()
                if self.warn_illegal and is_illegal(inst[0]):
                    warn("illegal opcode: {}[{:02X}]", line[0], inst[0])
                self.block_add(*inst)
                return

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


def warn_arg(ap, name, default=False):
    ap.add_argument(
        "-W{}".format(name),
        dest="warn_{}".format(name),
        default=default,
        action="store_true"
    )
    ap.add_argument(
        "-Wno-{}".format(name),
        dest="warn_{}".format(name),
        action="store_false"
    )


def main():
    ap = ArgumentParser(description="simple 6502 Assembler")
    ap.add_argument("-o", "--output", dest="output", default="a.prg",
                    type=FileType("wb"), help="output file")
    ap.add_argument("input", metavar="FILE", type=FileType("r"), nargs=1)
    warn_arg(ap, "illegal")
    args = ap.parse_args()
    MOS6502Parser(args.input[0], args.warn_illegal).write(args.output)


if __name__ == "__main__":
    main()
