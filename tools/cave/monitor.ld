/* Debug monitor placement: first page of the FIRM code cave and a reserved block of heap RAM.
   Must match CAVE / RAM in tools/cave/build.py. */
MEMORY
{
    CAVE (rx) : ORIGIN = 0xCAE000, LENGTH = 0x1000
    RAM (rw)  : ORIGIN = 0x878800, LENGTH = 0x400
}

SECTIONS
{
    .text : {
        KEEP(*(.text.head))
        KEEP(*(.text.entry))
        *(.text*)
        *(.rodata*)
    } > CAVE
    .data : { *(.data*) } > CAVE
    .bss (NOLOAD) : { *(.bss*) *(COMMON) } > RAM
    /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment) *(.ARM.attributes) }
}
ASSERT(SIZEOF(.data) == 0, "cave code has no loader: no initialised data")
