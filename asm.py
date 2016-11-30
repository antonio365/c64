#!/usr/bin/env python3

from argparse import ArgumentParser
from opcodes import OPCODES, is_illegal
from sys import stderr

lo = lambda x: x & 0xff
hi = lambda x: (x >> 8) & 0xff


def first_or_self(op, *args):
	for x in args:
		if x in op:
			x = op[x]
			return x[0] if type(x) is list else x
	raise ValueError("No such mode {} in {}".format(str(op), str(args)))


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
		parse_offset = 0
		for line in infh.readlines():
			for cc in self.comment_chars:
				comment = line.find(cc)
				if comment >= 0:
					line = line[:comment]
			colon = line.find(":")
			if colon >= 0:
				# todo: remove label from beginning of line
				label = 0
				line = line[colon + 1:].strip()
			line = line.split()
			if not len(line):
				continue
			if line[0].upper().startswith(".ORG"):
				parse_offset = 0
				assert(len(line) == 2)
				self.blocks.append({
					"org": self.parse_num(line[1]),
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
						op, line[1] if len(line) > 1 else None,
						parse_offset
					))
					break
			parse_offset = len(self.blocks[-1])

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
			if arg[0] == "0":
				use_wide = True
			num = int(arg)
		if return_use_wide:
			return use_wide, num
		return num

	@staticmethod
	def race(arg, op, shortmode, longmode):
		use_wide, num = MOS6502Parser.parse_num(arg, True)
		if shortmode in op and not (use_wide and longmode in op):
			return first_or_self(op, shortmode), num
		return first_or_self(op, longmode), lo(num), hi(num)

	@staticmethod
	def parse_op(op, arg, parse_offset):
		flags = (
			"NO_ARG", "A", "#", "(,X)", "(),Y", "()", ",X", ",Y", "USE_WIDE",
		)
		if arg is None:
			return first_or_self(op, "_", "a"),
		elif arg.upper() == "A":
			return first_or_self(op, "a"),
		elif arg[0] == "#":
			return first_or_self(op, "#"), MOS6502Parser.parse_num(arg[1:])
		elif arg[0] == "(" and arg[-3:].upper() == ",X)":
			return (
				first_or_self(op, "iz,x"),
				MOS6502Parser.parse_num(arg[1:-3])
			)
		elif arg[0] == "(" and arg[-3:].upper() == "),Y":
			return (
				first_or_self(op, "iz,y"),
				MOS6502Parser.parse_num(arg[1:-3])
			)
		elif arg[0] == "(" and arg[-1].upper() == ")":
			return (
				first_or_self(op, "ind"),
				MOS6502Parser.parse_num(arg[1:-1])
			)
		elif arg[-2:].upper() == ",X":
			return MOS6502Parser.race(arg[:-2], op, "zp,x", "abs,x")
		elif arg[-2:].upper() == ",Y":
			return MOS6502Parser.race(arg[:-2], op, "zp,y", "abs,y")
		if "r" in op:
			# todo: relative address support, label support
			raise NotImplementedError
		return MOS6502Parser.race(arg[:-2], op, "zp", "abs")

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
