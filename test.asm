.org $0801
.hex 0b 08 e0 07 9e 32 30 36 31 00 00 00

start1:
  jsr start2    ; .C:080d  20 30 08    JSR $0830
  lda #$60      ; .C:0810  A9 60       LDA #$60
  sta return    ; .C:0812  8D 15 08    STA $0815
return:
  nop           ; .C:0815  EA          NOP
  jmp start1    ; .C:0816  4C 0D 08    JMP $080D

.org $0830
start2:
  inc.abs $d020 ; .C:0830  EE 20 D0    INC $D020
  bne label     ; .C:0833  D0 03       BNE $0838
  inc $d021     ; .C:0835  EE 21 D0    INC $D021
label:
  bne start2    ; .C:0838  D0 F6       BNE $0830
  rts           ; .C:083a  60          RTS

.org $0900

.hex de ad be ef ; >C:0900  de ad be ef  00 00 00 00  00
