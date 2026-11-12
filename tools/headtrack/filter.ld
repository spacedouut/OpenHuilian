MEMORY {
  FLASH (rx) : ORIGIN = 0xCB0000, LENGTH = 0x2000
  RAM (rw) : ORIGIN = 0x878400, LENGTH = 0x300
}
SECTIONS {
  .text : { *(.text*) *(.rodata*) } > FLASH
  .bss (NOLOAD) : { *(.bss*) *(COMMON) } > RAM
  /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) }
}
