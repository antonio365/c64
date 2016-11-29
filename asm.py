#!/usr/bin/env python3

from argparse import ArgumentParser
from opcodes import OPCODES, is_illegal
from sys import stderr

lo = lambda x: x & 0xff
hi = lambda x: (x >> 8) & 0xff


def parse_num(s):
	if s[0] == "$":
		return int(s[1:], 16)
	return int(s)


def first_op(op, *args):
	for arg in args:
		if arg in op:
			if type(op[arg]) is list:
				return op[arg][0]
			else:
				return arg, op[arg]
	raise ValueError("No op found", op, args)


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
		print(args)
		for arg in args:
			self.blocks[-1]["data"].append(arg)

	def __init__(self, infh):
		self.blocks = []
		for line in infh.readlines():
			for cc in self.comment_chars:
				comment = line.find(cc)
				if comment >= 0:
					line = line[:comment]
			line = line.split()
			if not len(line):
				continue
			print(line)
			if line[0].upper().startswith(".ORG"):
				assert(len(line) == 2)
				self.blocks.append({
					"org": parse_num(line[1]),
					"data": bytearray(),
				})
				continue
			if line[0].upper().startswith(".HEX"):
				for x in line[1:]:
					num = int(x[-4:], 16)
					if len(x) > 2:
						self.block_add(lo(num))
						num >>= 8
					self.block_add(num)
				continue
			assert(len(line) in (1, 2))
			for mn, op in self.opcodes.items():
				if line[0].upper().startswith(mn):
					self.block_add(*self.parse_op(
						op, line[1] if len(line) > 1 else None
					))

	@staticmethod
	def parse_op(op, arg):
		if arg is None:
			return first_op(op, "_", "a")[1],
		elif arg[0] == "#":
			return first_op(op, "#")[1], parse_num(arg[1:])
		elif arg[-2:] == ",x":
			return first_op(op, "zp,x", "abs,x")[1], parse_num(arg[1:-3])
		elif arg[0] == "(" and arg[-3:] == ",x)":
			return first_op(op, "iz,x")[1], parse_num(arg[1:-3])
		elif arg[0] == "(" and arg[-3:] == "),y":
			return first_op(op, "iz,y")[1], parse_num(arg[1:-3])
		elif arg[0] == "(" and arg[-1] == ")":
			num = parse_num(arg[1:-3])
			return first_op(op, "ind")[1], lo(num), hi(num)
		num = parse_num(arg)
		if num < 256 and len(arg) < 4:
			mode = first_op(op, "zp", "abs")
			if mode[0] == "zp":
				return mode[1], num
			else:
				return mode[1], lo(num), hi(num)
		return first_op(op, "abs")[1], lo(num), hi(num)

	def dump(self):
		print("\n".join(str(line) for line in self.blocks))

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
			fh.write(block["data"])
			current += len(block["data"])
			if i + 1 < len(self.blocks):
				assert(self.blocks[i + 1]["org"] >= current)
				# add padding between blocks
				if self.blocks[i + 1]["org"] > current:
					fh.write(b"\0" * (self.blocks[i + 1]["org"] - current))


def main():
	MOS6502Parser.setup()
	ap = ArgumentParser(description="simple 6502 Assembler")
	ap.add_argument("--output", "-o", default="a.prg", help="output file")
	ap.add_argument('--dump', dest='dump', action='store_true')
	ap.add_argument("input", metavar="FILE", type=str, nargs=1)
	args = ap.parse_args()
	with open(args.input[0], "r") as infh:
		parser = MOS6502Parser(infh)
	if args.dump:
		parser.dump()
	with open(args.output, "wb") as outfh:
		parser.write(outfh)


if __name__ == "__main__":
	main()
