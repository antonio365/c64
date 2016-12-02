.org $0801
.hex 0b 08 e0 07 9e 32 30 36 31 00 00 00

start1:
  jsr start2    ; 080d jsr $0819
  lda #$60      ; 0810 lda #60
  sta return    ; 0812 sta $0815
return:
  nop           ; 0815 nop
  jmp start1    ; 0816 jmp $080d

start2:
  inc.abs $d020 ; 0819 inc $d020
  bne label     ; 081c bne $0821
  inc $d021     ; 081e inc $d021
label:
  bne start2    ; 0821 bne $0819
  rts           ; 0823 rts

.org $0900

.hex de ad be ef
