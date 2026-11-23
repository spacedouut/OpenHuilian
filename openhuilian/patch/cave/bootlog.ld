/* Boot log placement: second half of the debug monitor's cave page and 16 bytes of heap RAM just
   below the monitor's block. Must match CAVE / RAM in openhuilian/patch/cave/build_bootlog.py. */
MEMORY
{
    CAVE (rx) : ORIGIN = 0xCAE800, LENGTH = 0x800
    RAM (rw)  : ORIGIN = 0x8787F0, LENGTH = 0x10
}

SECTIONS
{
    .text : {
        KEEP(*(.text.entry))
        *(.text*)
        *(.rodata*)
    } > CAVE
    .data : { *(.data*) } > CAVE
    .bss (NOLOAD) : { *(.bss*) *(COMMON) } > RAM
    /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment) *(.ARM.attributes) }
}
ASSERT(SIZEOF(.data) == 0, "cave code has no loader: no initialised data")
