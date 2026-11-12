#!/usr/bin/env python3
"""Recover focused Thumb evidence with an installed PyGhidra/Ghidra.

No project/database writes: constructs an in-memory program from the supplied ELF.
All evidence files go to an existing --out scratch directory. Set GHIDRA_INSTALL_DIR.
"""
import argparse
import struct
from pathlib import Path

import pyghidra

ADDRESSES = [
    0xC58A5C, 0xC68924, 0xC6739C, 0xC68600, 0xC68284, 0xCAAAB0,
    0xCAB53C, 0xC589BC, 0xC59298, 0xC74F7C, 0xC74C88, 0xC683A8,
    0xC684D0, 0xC67374, 0xC5968C, 0xC596A4, 0xC74E14, 0xC74BE0,
    0xC679E0, 0xC67EA4, 0xCAA838, 0xCAA7D8, 0xCAAA0C, 0xCAA554,
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if not args.out.is_dir():
        parser.error("--out must be an existing scratch directory")
    pyghidra.start()
    # Ghidra classes become importable only after its JVM has started.
    from ghidra.app.cmd.disassemble import DisassembleCommand
    from ghidra.app.cmd.function import CreateFunctionCmd
    from ghidra.app.decompiler import DecompInterface
    from ghidra.program.database import ProgramDB
    from ghidra.program.model.lang import LanguageID
    from ghidra.program.util import DefaultLanguageService
    from ghidra.util.task import ConsoleTaskMonitor
    from java.io import ByteArrayInputStream
    from java.lang import Object
    from java.math import BigInteger

    language = DefaultLanguageService.getLanguageService().getLanguage(LanguageID("ARM:LE:32:Cortex"))
    consumer, monitor = Object(), ConsoleTaskMonitor()
    program = ProgramDB("headtrack", language, language.getDefaultCompilerSpec(), consumer)
    space = program.getAddressFactory().getDefaultAddressSpace()
    transaction = program.startTransaction("Explicit Thumb motion entries")
    elf = args.elf.read_bytes()
    offset = struct.unpack_from("<I", elf, 28)[0]
    size, count = struct.unpack_from("<HH", elf, 42)
    for i in range(count):
        kind, fileoff, va, _, length, _, _, _ = struct.unpack_from("<8I", elf, offset+i*size)
        if kind == 1:
            block = program.getMemory().createInitializedBlock(str(va), space.getAddress(va),
                ByteArrayInputStream(elf[fileoff:fileoff+length]), length, monitor, False)
            block.setExecute(True)
    context = program.getProgramContext()
    for value in ADDRESSES:
        address = space.getAddress(value)
        context.setValue(context.getRegister("TMode"), address, address, BigInteger.ONE)
    for value in ADDRESSES:
        address = space.getAddress(value)
        DisassembleCommand(address, None, True).applyTo(program, monitor)
        CreateFunctionCmd(address).applyTo(program, monitor)
    program.endTransaction(transaction, True)
    decompiler = DecompInterface()
    decompiler.openProgram(program)
    try:
        for value in ADDRESSES:
            function = program.getFunctionManager().getFunctionAt(space.getAddress(value))
            if function is None:
                raise RuntimeError(f"no function at {value:#x}")
            result = decompiler.decompileFunction(function, 60, monitor)
            if not result.decompileCompleted():
                raise RuntimeError(result.getErrorMessage())
            (args.out/f"{value:x}.c").write_text(result.getDecompiledFunction().getC())
            lines = [f"{ins.getAddress()} {ins}" for ins in
                     program.getListing().getInstructions(function.getBody(), True)]
            (args.out/f"{value:x}.asm").write_text("\n".join(lines)+"\n")
    finally:
        decompiler.dispose()
        program.release(consumer)


if __name__ == "__main__":
    main()
