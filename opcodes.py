#!/usr/bin/env python3

from collections import namedtuple
from sys import argv

Opcode = namedtuple("Opcode", ["mnemonic", "modes", "alias"])
Opcode.__new__.__defaults__ = ([], )

# _: implied / no argument
# a: accumulator
# #: immediate
# zp: zeropage
# zx: zeropage,x
# abs: absolute
# abs,x: absolute,x
# abs,y: absolute,y
# iz,x: (indexed,x)
# iz,y: (indexed),y
# ind: (absolute indirect)
# r: relative
OPCODES = (
	Opcode("BRK", {"_": 0x00}),
	Opcode("ORA", {
		"#": 0x09, "zp": 0x05, "zp,x": 0x15,
		"abs": 0x0D, "abs,x": 0x1D, "abs,y": 0x19,
		"iz,x": 0x01, "iz,y": 0x11,
	}),
	Opcode("JAM", {"_": [
		0x02, 0x12, 0x22, 0x32, 0x42, 0x52, 0x62, 0x72, 0x92, 0xB2, 0xD2, 0xF2
	]}, ("CRS", "KIL", "HLT")),
	Opcode("SLO", {
		"zp": 0x07, "zp,x": 0x17, "abs": 0x0F, "abs,x": 0x1F, "abs,y": 0x1B,
		"iz,x": 0x03, "iz,y": 0x13,
	}, ("ASO", )),
	Opcode("NOP", {
		"_": [0xEA, 0x1A, 0x3A, 0x5A, 0x7A, 0xDA, 0xFA],
		"#": [0x80, 0x82, 0x89, 0xC2, 0xE2],
		"zp": [0x04, 0x44, 0x64],
		"zp,x": [0x14, 0x34, 0x54, 0x74, 0xD4, 0xF4],
		"abs": 0x0C,
		"abs,x": [0x1C, 0x3C, 0x5C, 0x7C, 0xDC, 0xFC]}),
	Opcode("ASL", {
		"a": 0x0A, "zp": 0x06, "zp,x": 0x16, "abs": 0x0E, "abs,x": 0x1E
	}),
	Opcode("PHP", {"_": 0x08}),
	Opcode("ANC", {"#": [0x0B, 0x2B]}),
	Opcode("BPL", {"r": 0x10}),
	Opcode("CLC", {"_": 0x18}),
	Opcode("JSR", {"abs": 0x20}),
	Opcode("AND", {
		"#": 0x29, "zp": 0x25, "zp,x": 0x35,
		"abs": 0x2D, "abs,x": 0x3D, "abs,y": 0x39,
		"iz,x": 0x21, "iz,y": 0x31
	}),
	Opcode("RLA", {
		"zp": 0x27, "zp,x": 0x37, "abs": 0x2F, "abs,x": 0x3F, "abs,y": 0x3B,
		"iz,x": 0x23, "iz,y": 0x33
	}),
	Opcode("BIT", {"zp": 0x24, "abs": 0x2C}),
	Opcode("PLP", {"_": 0x28}),
	Opcode("ROL", {
		"a": 0x2A, "zp": 0x26, "zp,x": 0x36,
		"abs": 0x2E, "abs,x": 0x3E
	}),
	Opcode("BMI", {"r": 0x30}),
	Opcode("SEC", {"_": 0x38}),
	Opcode("RTI", {"_": 0x40}),
	Opcode("EOR", {
		"#": 0x49, "zp": 0x45, "zp,x": 0x55,
		"abs": 0x4D, "abs,x": 0x5D, "abs,y": 0x59,
		"iz,x": 0x41, "iz,y": 0x51
	}),
	Opcode("SRE", {
		"zp": 0x47, "zp,x": 0x57, "abs": 0x4F, "abs,x": 0x5F, "abs,y": 0x5B,
		"iz,x": 0x43, "iz,y": 0x53
	}, ("LSE", )),
	Opcode("LSR", {
		"a": 0x4A, "zp": 0x46, "zp,x": 0x56,
		"abs": 0x4E, "abs,x": 0x5E
	}),
	Opcode("PHA", {"_": 0x48}),
	Opcode("ASR", {"#": 0x4b}, ("ALR", )),
	Opcode("JMP", {"abs": 0x4c, "ind": 0x6c}),
	Opcode("BVC", {"r": 0x50}),
	Opcode("CLI", {"_": 0x58}),
	Opcode("PLA", {"_": 0x68}),
	Opcode("ADC", {
		"#": 0x69, "zp": 0x65, "zp,x": 0x75,
		"abs": 0x6D, "abs,x": 0x7D, "abs,y": 0x79,
		"iz,x": 0x61, "iz,y": 0x71
	}),
	Opcode("RTS", {"_": 0x60}),
	Opcode("RRA", {
		"zp": 0x67, "zp,x": 0x77, "abs": 0x6F, "abs,x": 0x7F, "abs,y": 0x7B,
		"iz,x": 0x63, "iz,y": 0x73
	}),
	Opcode("ROR", {
		"a": 0x6A, "zp": 0x66, "zp,x": 0x76,
		"abs": 0x6E, "abs,x": 0x7E
	}),
	Opcode("ARR", {"#": 0x6B}),
	Opcode("BVS", {"r": 0x70}),
	Opcode("SEI", {"_": 0x78}),
	Opcode("STA", {
		"zp": 0x85, "zp,x": 0x95, "abs": 0x8D, "abs,x": 0x9D, "abs,y": 0x99,
		"iz,x": 0x81, "iz,y": 0x91
	}),
	Opcode("SAX", {"zp": 0x87, "zp,y": 0x97, "abs": 0x8F, "iz,x": 0x83}),
	Opcode("STY", {"zp": 0x84, "zp,x": 0x94, "abs": 0x8C}),
	Opcode("STX", {"zp": 0x86, "zp,y": 0x96, "abs": 0x8E}),
	Opcode("DEY", {"_": 0x88}),
	Opcode("TXA", {"_": 0x8A}),
	Opcode("ANE", {"#": 0x8B}, ("XAA", )),
	Opcode("BCC", {"r": 0x90}),
	Opcode("SHA", {"abs,x": 0x93, "abs,y": 0x9F}, ("AHX", )),
	Opcode("TYA", {"_": 0x98}),
	Opcode("TXS", {"_": 0x9A}),
	Opcode("SHS", {"abs,x": 0x9B}, ("TAS", )),
	Opcode("SHY", {"abs,y": 0x9C}),
	Opcode("SHX", {"abs,y": 0x9E}),
	Opcode("LDY", {
		"#": 0xA0, "zp": 0xA4, "zp,x": 0xB4, "abs": 0xAC, "abs,x": 0xBC
	}),
	Opcode("LDA", {
		"#": 0xA9, "zp": 0xA5, "zp,x": 0xB5,
		"abs": 0xAD, "abs,x": 0xBD, "abs,y": 0xB9,
		"iz,x": 0xA1, "iz,y": 0xB1
	}),
	Opcode("LDX", {
		"#": 0xA2, "zp": 0xA6, "zp,y": 0xB6, "abs": 0xAE, "abs,y": 0xBE,
	}),
	Opcode("LAX", {
		"#": 0xAB, "zp": 0xA7, "zp,y": 0xB7, "abs": 0xAF, "abs,y": 0xBF,
		"iz,x": 0xA3, "iz,y": 0xB3,
	}),
	Opcode("TAY", {"_": 0xA8}),
	Opcode("TAX", {"_": 0xAA}),
	Opcode("LXA", {"#": 0xAB}), # also LAX#
	Opcode("BCS", {"r": 0xB0}),
	Opcode("CLV", {"_": 0xB8}),
	Opcode("TSX", {"_": 0xBA}),
	Opcode("LAE", {"abs,y": 0xBB}, ("LAS", "LAR")),
	Opcode("CPY", {"#": 0xC0, "zp": 0xC4, "abs": 0xCC}),
	Opcode("CMP", {
		"#": 0xC9, "zp": 0xC5, "zp,x": 0xD5,
		"abs": 0xCD, "abs,x": 0xDD, "abs,y": 0xD9,
		"iz,x": 0xC1, "iz,y": 0xD1,
	}),
	Opcode("DCP", {
		"zp": 0xC7, "zp,x": 0xD7, "abs": 0xCF, "abs,x": 0xDF, "abs,y": 0xDB,
		"iz,x": 0xC3, "iz,y": 0xD3,
	}),
	Opcode("DEC", {
		"zp": 0xC6, "zp,x": 0xD6, "abs": 0xCE, "abs,x": 0xDE,
	}),
	Opcode("INY", {"_": 0xC8}),
	Opcode("DEX", {"_": 0xCA}),
	Opcode("SBX", {"#": 0xCB}, ("AXS", )),
	Opcode("BNE", {"r": 0xD0}),
	Opcode("CLD", {"_": 0xD8}),
	Opcode("CPX", {"#": 0xE0, "zp": 0xE4, "abs": 0xEC}),
	Opcode("SBC", {
		"#": [0xE9, 0xEB], "zp": 0xE5, "zp,x": 0xF5,
		"abs": 0xED, "abs,x": 0xFD, "abs,y": 0xF9,
		"iz,x": 0xE1, "iz,y": 0xF1,
	}),
	Opcode("ISB", {
		"zp": 0xE7, "zp,x": 0xF7, "abs": 0xEF, "abs,x": 0xFF, "abs,y": 0xFB,
		"iz,x": 0xE3, "iz,y": 0xF3
	}, ("ISC", )),
	Opcode("INC", {"zp": 0xE6, "zp,x": 0xF6, "abs": 0xEE, "abs,x": 0xFE}),
	Opcode("INX", {"_": 0xE8}),
	Opcode("BEQ", {"r": 0xF0}),
	Opcode("SED", {"_": 0xF8}),
)

ILLEGAL = """
0011100100011001
0011100100111001
0011000100010001
0011100100111001
0011100100010001
0011100100111001
0011100100010001
0011100100111001
1011000101010001
0012000100022022
0001000100020001
0011000100020001
0011000100010001
0011100100111001
0011000100010001
0011100100111001
""".replace("\n", "")


def is_illegal(x):
	global ILLEGAL
	return int(ILLEGAL[x])


def compare_output():
	global OPCODES
	for op in OPCODES:
		for mode, v in op.modes.items():
			for _ in range(1 if type(v) is not list else len(v)):
				yield "{} {}".format(op.mnemonic, {
					"abs": "a",
					"abs,x": "a,x",
					"abs,y": "a,y",
					"zp": "z",
					"zp,x": "z,x",
					"zp,y": "z,y",
					"iz,x": "(z,x)",
					"iz,y": "(z),y",
					"a": "A",
					"r": "r",
					"#": "#",
					"ind": "(a)",
					"_": "i" if op.mnemonic not in(
						"BRK", "RTI", "RTS", "PHP", "PLP", "PHA", "PLA",
					) else "s"
				}[mode])


def main():
	global OPCODES
	assert(all([all(x in (
		"ind", "_", "#", "a", "abs", "abs,x", "abs,y",
		"zp", "zp,x", "zp,y", "iz,x", "iz,y", "r"
	) for x in op.modes.keys()) for op in OPCODES]))
	opc_list = sorted(compare_output())
	for x in range(256):
		found = False
		for op in OPCODES:
			for m in op.modes.values():
				if type(m) is list and x in m or m == x:
					found = True
					break
			if found:
				break
		assert(found)
	for x in range(256):
		assert(opc_list[x] == sorted([
			"BRK s",     "ORA (z,x)", "JAM i",     "SLO (z,x)", "NOP z",
			"ORA z",     "ASL z",     "SLO z",     "BPL r",     "ORA (z),y",
			"JAM i",     "SLO (z),y", "NOP z,x",   "ORA z,x",   "ASL z,x",
			"SLO z,x",   "JSR a",     "AND (z,x)", "JAM i",     "RLA (z,x)",
			"BIT z",     "AND z",     "ROL z",     "RLA z",     "BMI r",
			"AND (z),y", "JAM i",     "RLA (z),y", "NOP z,x",   "AND z,x",
			"ROL z,x",   "RLA z,x",   "RTI s",     "EOR (z,x)", "JAM i",
			"SRE (z,x)", "NOP z",     "EOR z",     "LSR z",     "SRE z",
			"BVC r",     "EOR (z),y", "JAM i",     "SRE (z),y", "NOP z,x",
			"EOR z,x",   "LSR z,x",   "SRE z,x",   "RTS s",     "ADC (z,x)",
			"JAM i",     "RRA (z,x)", "NOP z",     "ADC z",     "ROR z",
			"RRA z",     "BVS r",     "ADC (z),y", "JAM i",     "RRA (z),y",
			"NOP z,x",   "ADC z,x",   "ROR z,x",   "RRA z,x",   "NOP #",
			"STA (z,x)", "NOP #",     "SAX (z,x)", "STY z",     "STA z",
			"STX z",     "SAX z",     "BCC r",     "STA (z),y", "JAM i",
			"SHA a,x",   "STY z,x",   "STA z,x",   "STX z,y",   "SAX z,y",
			"LDY #",     "LDA (z,x)", "LDX #",     "LAX (z,x)", "LDY z",
			"LDA z",     "LDX z",     "LAX z",     "BCS r",     "LDA (z),y",
			"JAM i",     "LAX (z),y", "LDY z,x",   "LDA z,x",   "LDX z,y",
			"LAX z,y",   "CPY #",     "CMP (z,x)", "NOP #",     "DCP (z,x)",
			"CPY z",     "CMP z",     "DEC z",     "DCP z",     "BNE r",
			"CMP (z),y", "JAM i",     "DCP (z),y", "NOP z,x",   "CMP z,x",
			"DEC z,x",   "DCP z,x",   "CPX #",     "SBC (z,x)", "NOP #",
			"ISB (z,x)", "CPX z",     "SBC z",     "INC z",     "ISB z",
			"BEQ r",     "SBC (z),y", "JAM i",     "ISB (z),y", "NOP z,x",
			"SBC z,x",   "INC z,x",   "ISB z,x",   "PHP s",     "ORA #",
			"ASL A",     "ANC #",     "NOP a",     "ORA a",     "ASL a",
			"SLO a",     "CLC i",     "ORA a,y",   "NOP i",     "SLO a,y",
			"NOP a,x",   "ORA a,x",   "ASL a,x",   "SLO a,x",   "PLP s",
			"AND #",     "ROL A",     "ANC #",     "BIT a",     "AND a",
			"ROL a",     "RLA a",     "SEC i",     "AND a,y",   "NOP i",
			"RLA a,y",   "NOP a,x",   "AND a,x",   "ROL a,x",   "RLA a,x",
			"PHA s",     "EOR #",     "LSR A",     "ASR #",     "JMP a",
			"EOR a",     "LSR a",     "SRE a",     "CLI i",     "EOR a,y",
			"NOP i",     "SRE a,y",   "NOP a,x",   "EOR a,x",   "LSR a,x",
			"SRE a,x",   "PLA s",     "ADC #",     "ROR A",     "ARR #",
			"JMP (a)",   "ADC a",     "ROR a",     "RRA a",     "SEI i",
			"ADC a,y",   "NOP i",     "RRA a,y",   "NOP a,x",   "ADC a,x",
			"ROR a,x",   "RRA a,x",   "DEY i",     "NOP #",     "TXA i",
			"ANE #",     "STY a",     "STA a",     "STX a",     "SAX a",
			"TYA i",     "STA a,y",   "TXS i",     "SHS a,x",   "SHY a,y",
			"STA a,x",   "SHX a,y",   "SHA a,y",   "TAY i",     "LDA #",
			"TAX i",     "LXA #",     "LDY a",     "LDA a",     "LDX a",
			"LAX a",     "CLV i",     "LDA a,y",   "TSX i",     "LAE a,y",
			"LDY a,x",   "LDA a,x",   "LDX a,y",   "LAX a,y",   "INY i",
			"CMP #",     "DEX i",     "SBX #",     "CPY a",     "CMP a",
			"DEC a",     "DCP a",     "CLD i",     "CMP a,y",   "NOP i",
			"DCP a,y",   "NOP a,x",   "CMP a,x",   "DEC a,x",   "DCP a,x",
			"INX i",     "SBC #",     "NOP i",     "SBC #",     "CPX a",
			"SBC a",     "INC a",     "ISB a",     "SED i",     "SBC a,y",
			"NOP i",     "ISB a,y",   "NOP a,x",   "SBC a,x",   "INC a,x",
			"ISB a,x"
		])[x])



if __name__ == "__main__":
	main()
