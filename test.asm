.org $0801 ; this is an inline comment
; this is more comment
.hex 0b 08 e0 07 9e 32 30 36 31 00 00 00

  inc $d020
  bne label
  inc $d021
label:
  jmp $080d
  rts

.org $0900

.hex de ad be ef
