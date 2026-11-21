# Set up REA and Hopper

[REA](https://github.com/morluto/rea) drives Hopper from a command line or an MCP client. This repo uses it on macOS to decompile the FIRM, OTAP, bootloader and mask-ROM images. Hopper does not run on the older Ubuntu release the Linux agents use, so this is macOS only.

## Install

```sh
tools/setup-rea-macos.sh
```

The script is safe to run again. It does four things.

1. Downloads Node.js 24.22.3 from nodejs.org, checks its SHA-256 and unpacks it to `~/.local/share/rea-node`. REA 6.10.1 rejects Node older than 22.23.4, 24.22.1 or 26.12.1.
2. Installs `rea-agents@6.10.1` from npm into that runtime.
3. Turns on Spotlight indexing for the data volume. Hopper's launcher locates the app through Spotlight and fails with "Hopper has not been found" without it.
4. Runs `rea setup --yes --all-detected --install-hopper`. This downloads Hopper from hopperapp.com, checks its code signature, copies it to `~/Applications` and registers the REA MCP server and skill with each agent client it finds.

Add `~/.local/share/rea-node/bin` to `PATH`. For a client `rea setup` does not know, register a stdio MCP server with the command `~/.local/share/rea-node/bin/node ~/.local/share/rea-node/bin/rea mcp`.

## Two prompts that need a person

Both appear on the first analysis and can't be scripted.

| Prompt | Answer |
|---|---|
| Hopper's license sheet | Validate a license file, or choose Try the Demo. The demo sheet returns each time Hopper starts, and REA times out waiting for it |
| macOS "wants access to control Hopper Disassembler" | Allow. It is asked once for each controlling app |

## Analyze the firmware

Hopper and REA both refuse headerless images, so wrap the partitions in ELFs first. The inputs are private; keep the ELFs and any output outside this repo.

```sh
python3 -m openhuilian.format.h3pro_elf "$OPENHUILIAN_STOCK_UP" ~/rea-work
rea inspect ~/rea-work/firm.elf --provider hopper --json
rea decompile ~/rea-work/boot.elf 0x860168 --provider hopper --json
```

The first call on an image waits for Hopper's analysis. Set `REA_HOPPER_STARTUP_TIMEOUT_MS=240000` if it times out. Later calls on the same image take about two seconds.

Hopper finds few procedures in these ELFs because they have no section headers or symbols. `rea decompile` returns "No procedure exists at the requested address" for code Hopper did not reach, which includes the exception handlers. Disassemble those with Capstone instead.

[Chip peripherals](../research/chip-peripherals.md) lists what this setup found.
