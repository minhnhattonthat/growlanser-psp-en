; vwf.asm: proportional English text for Growlanser PSP (armips, applied by tools/insert.py to BOOT.BIN, the
; decrypted module; tools/sign.py re-signs it into EBOOT.BIN). Port of the PS1 project's asm/vwf.asm
; (../growlanser-en): same text engine, same 4bpp canvas, same pair codes (tools/enfont.py). docs/re/text.md "VWF".
;
; The printer 0x088748A0 (frame 0x80; s6 = column, s5 = row) draws glyphs through two routines that read the font:
;   0x08876C14 (col, row, code): normal, x = col*12 texels, y = row*16+2; jal at 0x0887501C (a1 = s5) and
;              0x088750F8 (a1 = s5 + 1), then jal WAIT 0x0886BF54, then s6 += 1.
;   0x0887705C (col, row, code): double size, y = row*16+6; jal at 0x08874CE0, then WAIT, then s6 += 2.
; Canvas struct 0x08CDE894 (base1, stride1, split column, -, base2, stride2, ...; +0x20 = u16 text colour), font
; pointer 0x08CDE890. 4bpp, low nibble = left texel, shadow colour 5 below and below-right of ink.
;
; PRX rule (tools/prxrel.py): a word with an R_MIPS_26 relocation gets base >> 2 added to its target field at load,
; so at those sites only j/jal with module-relative targets go in (CALL_REL / JUMP_REL macros); other words are free.
; The module always loads at 0x08804000 (PPSSPP, PSP, Vita; cheat codes rely on it), so code here uses absolute RAM
; addresses. shortcut: no relocations for the new code; add them if a loader ever moves the module.
; Code and the English font sit in the font's last kanji cells 0x6A0-0x835 (unused once the script is English).

.psp
.open "BOOT.BIN", 0x08803F60             ; .text/.rodata: RAM = file + 0x08803F60

MODBASE    equ 0x08804000
WAIT       equ 0x0886BF54
PAIR       equ 0x0800
CANVAS     equ 0x08CDE894
FONTPTR    equ 0x08CDE890
EXTENT     equ 0x08CD1BBC                ; s16 max column of a glyph start (pre-parser), page print width source
FREE_START equ 0x0892E7B8                ; font cell 0x6A0 (BOOT.BIN 0x12A878)
FREE_END   equ 0x089303E4                ; end of the font (cell 0x836, BOOT.BIN 0x12C4A4)
.include "gen.inc"                       ; written by tools/insert.py (CONT_RA1, CONT_RA2: page-path callers)

.macro CALL_REL, dest                    ; jal at a relocated site
    .word 0x0C000000 | (((dest) - MODBASE) >> 2)
.endmacro
.macro JUMP_REL, dest                    ; j at a relocated site
    .word 0x08000000 | (((dest) - MODBASE) >> 2)
.endmacro

; Glyph calls: vwf_std / vwf_big set s6 to the new column themselves; the s6 step after WAIT becomes a nop.
.org 0x0887501C
    CALL_REL vwf_std                      ; was jal 0x08876C14 (delay: move a1, s5)
.org 0x08875030
    nop                                  ; was addiu s6, s6, 1
.org 0x088750F8
    CALL_REL vwf_std                      ; was jal 0x08876C14 (delay: addiu a1, s5, 1)
.org 0x0887510C
    nop                                  ; was addiu s6, s6, 1
.org 0x08874CE0
    CALL_REL vwf_big                      ; was jal 0x0887705C (delay: move a1, s5)
.org 0x08874CF0
    nop                                  ; was addiu s6, s6, 2

; Dialogue typewriter (byte 0x08CD1B63 = 1): one code per frame through a 1x1-column window at the cursor, so every
; pair sat in its own 12 px cell. Take the page-at-once path (the one used when the flag is 0) instead: text
; appears a page (or up to the next wait code) at a time.
.org 0x08869BCC
    nop                                  ; was beq s2, a0, 0x0886A8C0 (typewriter); delay "lui v1" stays
.org 0x08869DCC
    nop                                  ; was beq s2, a0, 0x0886A93C (typewriter); delay "lui a0" stays

; Message pre-parser (0x088673D8): column s1 += 1 per glyph code (2 at double size), extent EXTENT = max start
; column, which later becomes the page print width. Advance s1 the way the printer's s6 moves instead.
.org 0x088677F4
    nop                                  ; was addiu s1, s1, 1
    JUMP_REL vwf_measure1                 ; was j 0x088675D4 (delay: move t8, s2)
.org 0x08867A58
    nop                                  ; was addiu s1, s1, 2
    JUMP_REL vwf_measure2                 ; was j 0x088675D4 (delay: move t8, s2)

; Printer entry: flag a new string, so its first glyph starts at its own column (a second string on the same row
; must not continue the first one's pen). Continuations of a message (page path resuming after a wait code) flag -1:
; vwf_draw keeps the pen if they resume at the column the last glyph ended in.
.org 0x088748A0
    j       vwf_newstr
    addiu   sp, sp, -0x80                ; the printer's first instruction

; Popup 0x08871B30 (field-menu bubbles boot.sys, place names; PS1 0x8006BA48): frame = 12 px per code (s5 = code
; count, used only for that at 0x08871C8C). Make s5 the text's pixel width and the frame s5 px. 0x08871C00 is the
; empty-string branch target (a0 = 0): its word sets v0 = 0 there, and is the jal's delay slot otherwise.
.org 0x08871BFC
    jal     popup_width                  ; a1 = string start (was subu a0, v1, a1 / srl / addu / sra s5, v0, 1)
    move    v0, zero
    move    s5, v0
    nop
.org 0x08871C98
    move    v1, s5                       ; was subu v1, v0, v1 (16 * s5 - 4 * s5)

.headersize 0x08803F40                   ; .data: RAM = file + 0x08803F40
.org FREE_START
vwf_newstr:
    sw      s0, 0x50(sp)                 ; was at 0x088748A4
    move    t9, sp                       ; new string (nonzero)
    li      t8, 0x08868504               ; return address in the print wrapper 0x08868480 (frame 0x30, ra at +0x20)
    bne     ra, t8, @@flag
    lw      t8, 0xA0(sp)                 ; the wrapper's caller
    li      t7, CONT_RA1
    beq     t8, t7, @@cont
    nop
    li      t7, CONT_RA2
    bne     t8, t7, @@flag
    nop
@@cont:
    li      t9, -1
@@flag:
    li      t8, vwf_state
    j       0x088748A8                   ; lw s0, 0x98(sp) ...
    sw      t9, 12(t8)

; Windows draw interleaved (typewriter text beside a name tag), so the x is kept per canvas: 4 slots of
; (canvas base1, texel x, last col returned, last row), replaced round-robin.
.align 4
vwf_state:                               ; 0 scale, 4 y0, 8 next slot to replace, 12 new-string flag, 16 slots
    .word 1, 0, 0, 0
    .word 0, 0, -1, -1
    .word 0, 0, -1, -1
    .word 0, 0, -1, -1
    .word 0, 0, -1, -1

vwf_std:
    li      a3, 1
    b       vwf_draw
    li      t0, 2
vwf_big:
    li      a3, 2
    li      t0, 6

; a0 col, a1 row, a2 code, a3 scale, t0 y offset in the row. Sets s6 = new col (the printer's column register).
vwf_draw:
    addiu   sp, sp, -0x28
    sw      ra, 0x24(sp)
    sw      s0, 0x10(sp)
    sw      s1, 0x14(sp)
    sw      s2, 0x18(sp)
    sw      s3, 0x1C(sp)
    li      s3, vwf_state
    lw      t3, 12(s3)                   ; new string: resync below
    sw      zero, 12(s3)
    sw      a3, 0(s3)
    sll     t1, a1, 4
    addu    t1, t1, t0
    sw      t1, 4(s3)                    ; y0 = row * 16 + offset
    li      t0, CANVAS
    lw      t9, 0(t0)                    ; canvas base1 now
    addiu   t4, s3, 16
    li      t5, 4
@@find:
    lw      t6, 0(t4)
    beq     t6, t9, @@found
    addiu   t5, t5, -1
    bnez    t5, @@find
    addiu   t4, t4, 16
    lw      t6, 8(s3)                    ; no slot for this canvas: take the next one
    addiu   t7, t6, 1
    andi    t7, t7, 3
    sw      t7, 8(s3)
    sll     t6, t6, 4
    addu    t4, s3, t6
    addiu   t4, t4, 16
    sw      t9, 0(t4)
    b       @@resync
    nop
@@found:
    lw      t1, 8(t4)
    lw      t2, 12(t4)
    lw      s0, 4(t4)
    addiu   t5, t3, 1
    bnez    t5, @@notcont
    nop
    beq     t1, a0, @@go                 ; continuation at the last glyph's column (its row origin may have moved)
    nop
    b       @@resync
    nop
@@notcont:
    bnez    t3, @@resync
    nop
    bne     t1, a0, @@resync
    nop
    beq     t2, a1, @@go
    nop
@@resync:
    sll     s0, a0, 1
    addu    s0, s0, a0
    sll     s0, s0, 2                    ; x = col * 12
@@go:
    move    s3, t4                       ; this canvas's slot
    move    s1, a1
    move    s2, a2
    sltiu   t0, s2, PAIR
    bnez    t0, @@legacy
    nop
    sltiu   t0, s2, PAIR + 0x4000
    beqz    t0, @@legacy
    nop
    addiu   t0, s2, -PAIR
    move    a0, s0
    jal     vwf_index
    srl     a2, t0, 7                    ; first letter
    move    s0, v0
    andi    a2, s2, 0x7F                 ; second letter, 0 = none
    beqz    a2, @@done
    nop
    jal     vwf_index
    move    a0, s0
    b       @@done
    move    s0, v0
@@legacy:
    li      t0, FONTPTR
    lw      t0, 0(t0)                    ; game font base
    sll     t1, s2, 3
    addu    t1, t1, s2
    sll     t1, t1, 1
    addu    a2, t0, t1
    move    a0, s0
    jal     vwf_glyph
    li      a3, 12
    move    s0, v0
@@done:
    addiu   t0, s0, 11
    li      t1, 12
    divu    t0, t1
    mflo    s6                           ; col = ceil(x / 12), straight into the printer's s6
    sw      s0, 4(s3)
    sw      s6, 8(s3)
    sw      s1, 12(s3)
    lw      ra, 0x24(sp)
    lw      s0, 0x10(sp)
    lw      s1, 0x14(sp)
    lw      s2, 0x18(sp)
    lw      s3, 0x1C(sp)
    jr      ra
    addiu   sp, sp, 0x28

; vwf_glyph for charset index a2 at texel a0. v0 = new texel x.
vwf_index:
    li      t0, en_widths
    addu    t0, t0, a2
    lbu     a3, 0(t0)
    sll     t1, a2, 3
    addu    t1, t1, a2
    sll     t1, t1, 1
    li      a2, en_glyphs
    j       vwf_glyph
    addu    a2, a2, t1

; Draw one 12x12 1bpp glyph (18 bytes, rows MSB-first) at texel a0, font columns 0..a3-1, scaled by
; vwf_state.scale (1 or 2) from canvas row vwf_state.y0, with the game's drop shadow (colour 5 below and
; below-right of ink). v0 = a0 + a3 * scale.
; Registers: a0 x, a2 src, a3 columns, t0 canvas struct, t2 split texel S, t3 colour, t8 y0, t9 previous row,
; v1 row, t4 row bits, t5 shadow bits, s0/s1 canvas 1 row + stride, s2/s3 canvas 2 row + stride, s4 scale,
; s5 sub-column, s6 column, s7 column mask, fp texel x of the column.
vwf_glyph:
    addiu   sp, sp, -0x28
    sw      s0, 0x00(sp)
    sw      s1, 0x04(sp)
    sw      s2, 0x08(sp)
    sw      s3, 0x0C(sp)
    sw      s4, 0x10(sp)
    sw      s5, 0x14(sp)
    sw      s6, 0x18(sp)
    sw      s7, 0x1C(sp)
    sw      fp, 0x20(sp)
    li      t0, vwf_state
    lw      s4, 0(t0)                    ; scale
    lw      t8, 4(t0)                    ; y0
    li      t0, CANVAS
    lw      t1, 8(t0)                    ; split column
    lbu     t3, 0x20(t0)                 ; text colour (u16 at CANVAS + 0x20)
    sll     t2, t1, 1
    addu    t2, t2, t1
    sll     t2, t2, 2                    ; S = split * 12 texels
    andi    t3, t3, 0xF
    move    v1, zero                     ; glyph row r = 0..12 (12 = shadow only)
    move    t9, zero                     ; previous row bits
@@row:
    move    t4, zero
    sltiu   t5, v1, 12
    beqz    t5, @@have
    sll     t5, v1, 1
    addu    t5, t5, v1
    srl     t6, t5, 1                    ; byte = 12r / 8
    addu    t6, a2, t6
    lbu     t4, 0(t6)
    lbu     t7, 1(t6)
    andi    t5, v1, 1
    bnez    t5, @@odd
    nop
    sll     t4, t4, 4
    b       @@cmb
    srl     t7, t7, 4
@@odd:
    andi    t4, t4, 0xF
    sll     t4, t4, 8
@@cmb:
    or      t4, t4, t7
    sll     t4, t4, 4                    ; bit 15 = column 0
@@have:
    srl     t5, t9, 1
    or      t5, t5, t9
    nor     t6, t4, zero
    and     t5, t5, t6                   ; shadow = (prev | prev >> 1) & ~cur
    move    t9, t4
    or      t6, t4, t5
    beqz    t6, @@next
    nop
    mult    v1, s4
    lw      s1, 4(t0)                    ; stride1
    lw      s3, 0x14(t0)                 ; stride2
    mflo    t6
    addu    t6, t6, t8                   ; canvas y = y0 + r * scale
    mult    t6, s1
    lw      s0, 0(t0)
    lw      s2, 0x10(t0)
    mflo    t7
    addu    s0, s0, t7                   ; canvas 1 row
    mult    t6, s3
    mflo    t7
    addu    s2, s2, t7                   ; canvas 2 row (its texel 0 = S)
    move    s6, zero                     ; font column
    ori     s7, zero, 0x8000             ; column mask
@@px:
    and     t6, t4, s7
    bnez    t6, @@put
    move    t7, t3                       ; ink
    and     t6, t5, s7
    beqz    t6, @@pnext
    nop
    li      t7, 5                        ; shadow
@@put:
    mult    s6, s4
    move    s5, zero
    mflo    fp
    addu    fp, fp, a0                   ; texel x of this font column
@@sub:
    addu    t1, fp, s5                   ; X
    andi    a1, t1, 1
    sll     a1, a1, 2                    ; nibble shift: odd texel = high nibble
    sltu    t6, t1, t2
    beqz    t6, @@c2
    nop
    srl     t1, t1, 1
    addu    t1, t1, s0                   ; byte in canvas 1
    b       @@rmw
    move    v0, s1
@@c2:
    subu    t1, t1, t2
    srl     t1, t1, 1
    addu    t1, t1, s2                   ; byte in canvas 2
    move    v0, s3
@@rmw:
    li      t6, 0xF
    sllv    t6, t6, a1
    nor     t6, t6, zero                 ; keep mask
    sllv    a1, t7, a1                   ; value in place
    lbu     at, 0(t1)
    and     at, at, t6
    or      at, at, a1
    sb      at, 0(t1)
    addiu   at, s4, -1
    beqz    at, @@subnext                ; scale 1: one canvas row
    addu    t1, t1, v0
    lbu     at, 0(t1)                    ; scale 2: the row below too
    and     at, at, t6
    or      at, at, a1
    sb      at, 0(t1)
@@subnext:
    addiu   s5, s5, 1
    sltu    t6, s5, s4
    bnez    t6, @@sub
    nop
@@pnext:
    addiu   s6, s6, 1
    sltu    t6, s6, a3
    bnez    t6, @@px
    srl     s7, s7, 1
@@next:
    addiu   v1, v1, 1
    sltiu   t6, v1, 13
    bnez    t6, @@row
    nop
    mult    a3, s4
    lw      s0, 0x00(sp)
    lw      s1, 0x04(sp)
    lw      s2, 0x08(sp)
    lw      s3, 0x0C(sp)
    lw      s4, 0x10(sp)
    lw      s5, 0x14(sp)
    lw      s6, 0x18(sp)
    lw      s7, 0x1C(sp)
    lw      fp, 0x20(sp)
    mflo    v0
    addu    v0, v0, a0
    jr      ra
    addiu   sp, sp, 0x28

; vwf_measure: pre-parser glyph step (v0 = scale, s2 = just past the code, s1 = its column; t8 = s2 already). Keeps
; (x, col) like vwf_state: x resyncs to s1 * 12 when the parser moved s1 itself (new line, indent). Every register
; but s1 and v0 is kept (the parser's live temporaries are not mapped). Continues at the loop head 0x088675D4.
vwf_measure1:
    b       vwf_measure
    li      v0, 1
vwf_measure2:
    li      v0, 2
vwf_measure:
    addiu   sp, sp, -0x30
    sw      ra, 0x00(sp)
    sw      a0, 0x04(sp)
    sw      v1, 0x08(sp)
    sw      t3, 0x0C(sp)
    sw      t4, 0x10(sp)
    sw      t5, 0x14(sp)
    sw      t6, 0x18(sp)
    sw      t7, 0x1C(sp)
    sw      t8, 0x20(sp)
    sw      t9, 0x24(sp)
    lhu     a0, -2(s2)
    jal     vwf_width
    move    t3, v0
    multu   v0, t3
    li      t4, vwf_mstate
    lw      t5, 0(t4)                    ; x
    lw      t6, 4(t4)                    ; the column that x belongs to
    mflo    v0                           ; advance in texels
    beq     t6, s1, @@go
    nop
    sll     t5, s1, 1
    addu    t5, t5, s1
    sll     t5, t5, 2                    ; x = s1 * 12
@@go:
    addu    t5, t5, v0
    addiu   t6, t5, 11
    li      t7, 12
    divu    t6, t7
    mflo    s1                           ; s1 = ceil(x / 12)
    sw      t5, 0(t4)
    sw      s1, 4(t4)
    li      t4, EXTENT
    lh      t6, 0(t4)                    ; the extent holds the glyph's first column; a wide code reaches s1 - 1
    addiu   t7, s1, -1
    slt     t8, t6, t7
    beqz    t8, @@done
    nop
    sh      t7, 0(t4)
@@done:
    lw      ra, 0x00(sp)
    lw      a0, 0x04(sp)
    lw      v1, 0x08(sp)
    lw      t3, 0x0C(sp)
    lw      t4, 0x10(sp)
    lw      t5, 0x14(sp)
    lw      t6, 0x18(sp)
    lw      t7, 0x1C(sp)
    lw      t8, 0x20(sp)
    lw      t9, 0x24(sp)
    j       0x088675D4
    addiu   sp, sp, 0x30

; vwf_width: a0 = glyph code; v0 = advance in font pixels as vwf_draw draws it (pairs from en_widths, game glyphs
; 12). Uses t7-t9, v1 only.
vwf_width:
    beqz    a0, @@ret
    ori     v0, zero, 12
    sltiu   t8, a0, PAIR
    bnez    t8, @@ret
    sltiu   t8, a0, PAIR + 0x4000
    beqz    t8, @@ret
    addiu   t8, a0, -PAIR
    srl     t7, t8, 7
    li      v1, en_widths
    addu    t7, v1, t7
    lbu     v0, 0(t7)
    andi    t8, t8, 0x7F
    beqz    t8, @@ret                    ; no second letter
    addu    t8, v1, t8
    lbu     t8, 0(t8)
    addu    v0, v0, t8
@@ret:
    jr      ra
    nop

; popup_width: v0 = pixel width of the string at a1 (FFFF ends). Uses a0, v1, t4-t9 (free in 0x08871B30 there).
popup_width:
    move    t5, a1
    move    t6, ra
    move    t4, zero
@@next:
    lhu     a0, 0(t5)
    ori     t9, zero, 0xFFFF
    beq     a0, t9, @@end
    addiu   t5, t5, 2
    jal     vwf_width
    nop
    b       @@next
    addu    t4, t4, v0
@@end:
    jr      t6
    move    v0, t4

.align 4
vwf_mstate:                              ; x, col
    .word 0, -1
en_widths:
    .incbin "en_widths.bin"
en_glyphs:
    .incbin "en_glyphs.bin"
vwf_end:
.if vwf_end > FREE_END
    .error "vwf.asm code + font past the font's end"
.endif

.close
