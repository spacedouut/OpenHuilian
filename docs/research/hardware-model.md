# Hardware model

[`openhuilian/emu/machine.py`](../../openhuilian/emu/machine.py) and [`chip.py`](../../openhuilian/emu/chip.py) model the 377H3 closely enough to run a stock image from power-on: mask ROM, BOOT, FIRM, the scheduler and the idle task. [`boot_check.py`](../../openhuilian/emu/boot_check.py) runs that boot and [`machine_test.py`](../../openhuilian/emu/machine_test.py) tests the registers one by one.

Every register behavior here was read from what stock code does with it (which bit it sets, which bit it then waits for) while running the `2607061716` image and the mask ROM in the model. Nothing was measured on a bud. A model that lets the code proceed is not proof the real register works that way.

[`h3emu.py`](../../openhuilian/emu/h3emu.py) is the older rehost. It starts in FIRM, answers ROM calls with `bx lr` plus a few named helpers, and reads every peripheral as zero. It is still what the patch checks use.

## What the model fixes

| h3emu | Machine + chip |
|---|---|
| ROM is `bx lr` | The real ROM runs from its reset vector when a dump is supplied |
| Starts at the FIRM entry with ROM `.data` unset. The scheduler start then asks for a zero-size idle stack and panics | ROM start-up, flash header check, BOOT and FIRM run in order |
| No exceptions | SVC, PendSV, SysTick and external IRQs are taken with stacking, MSP/PSP, priorities, PRIMASK/BASEPRI and exception return, so ROM FreeRTOS switches real tasks |
| No time | SysTick and the 1 MHz counter advance with executed instructions. Busy-wait delays and WFI skip forward |
| Peripheral reads are 0, or `--unstick` flips bits | Each block below answers the way the code expects. Anything else reads back what was written and is listed in the report |
| Flash is a byte array | A 25-series NOR behind the controller: write enable, erase to FF, program only clears bits, 256 B page wrap, busy flag. A CPU store into the XIP window is a fault |
| A loop on an unmodelled bit spins until the budget ends | The run stops and names the register and PC after 2,000,000 reads of one register |

## Boot as the model runs it

Times are emulated milliseconds at 16 MHz with one instruction per cycle, so they are rough.

| Time | Step |
|---|---|
| 0 | ROM reset vector `0x40`. Stage numbers 1 to 5 go to `0x40000100` |
| 3 to 504 | ROM waits 500 ms for a UART download |
| 504 to 633 | ROM probes the card host at `0x40003000`, then the SPI flash |
| 633 | ROM reads the 92 B header at flash 0, runs it through the controller's CRC unit and compares with the word at `0x5C`. A mismatch is stage `0x1013`, and the ROM retries, tries a second header at `0x1000`, and goes back to the download wait. Stage `0x1015` is a pass |
| 634 | ROM loads BOOT (`0x1CF0` bytes from `0x60`) and jumps to it |
| 635 | BOOT prints `#` on UART0 and reports stages 8, 9, `0xA`, `0xB` |
| 666 | FIRM reads the index and its partitions, reads the JEDEC ID and status, copies its RAM block |
| 0.7 to 3.7 s | Scheduler starts (one SVC). Drivers come up. FIRM finds PSMP blank in the stock `.up` and writes its first records at `0xFC000` |
| 3.7 s | Idle task: SysTick off, every IRQ but 48 disabled, supply rail lowered, WFI |

Raising IRQ 48 wakes it. The handler at `0x80AD13` runs, the tasks run, and it sleeps again.

## Modelled blocks

| Address | Model | Behavior, as stock code uses it |
|---|---|---|
| `0xE000E000` | `Machine` | SysTick, NVIC enable/pending/priority, ICSR, VTOR, SHPR. SysTick with CLKSOURCE 0 counts a 1 MHz reference. FIRM loads 999 for a 1 kHz tick |
| `0x30000000` | `FlashController` | `+0x10` command (bit 31 go, low byte SPI opcode), `+0x14` length minus 1, `+0x18` flash address, `+0x1C` RAM buffer, `+0x0C` bit 1 done, write 1 to clear. `+0x60` bit 0 enables a CRC-16/CCITT-FALSE unit over bytes read, `+0x64` seed, `+0x6C` result. `+0x11C` cache flush, self-clearing. IRQ 25 or 50, whichever is enabled |
| `0x40000000` | `System` | `+0x100` boot stage number, write-only |
| `0x40080000` | `Clocks` | `+0x00`, `+0x08`, `+0x10`: three PLLs, bits 30 and 31 enable, bit 28 lock. Clock enables at `+0x60` to `+0x78` read back |
| `0x40082000` | `MicrosecondTimer` | `+0x104` low and `+0x108` high word of a free-running 1 MHz counter |
| `0x40085000` | `Pmu` | `+0x100` bit 31 reset, self-clearing. `+0x104` bit 31 go/busy, bits 8 to 15 register, low byte `0x60` write or `0x61` read. `+0x108` write data, `+0x10C` read data, `+0x110` bits 12 to 15 error. `+0x98` request bits 19 and 16 are acknowledged in bits 29 and 25. `+0x84` measured slow-clock frequency in Hz. `+0xC0` rail voltage, `+0xD0` bit 3 starts a rail change, bit 1 reports ready, bit 2 acknowledges. IRQ 48 is the wake-up |
| `0x40089000` | `I2CMaster` | `+0x00` bit 31 reset. `+0x04` bit 31 go/busy, bit 0 START plus address byte, bit 3 data byte, bit 1 STOP. `+0x08` TX, `+0x0C` RX, `+0x10` bit 15 NACK, write 1 to clear. FIRM probes 7-bit address `0x60` three times |
| `0x40090000`, `0x40091000`, `0x40092000` | `Uart` | `+0x00` data, `+0x08` bit 4 ready to send. Nothing drives RX |
| `0x40003000`, `0x40003004` | self-clearing bits | Card host reset bits 0 to 2 and command start bit 31 |
| `0x40009400` | self-clearing bit | Indexed register port: bit 31 go/busy, bits 8 to 12 bank, bits 0 to 6 register, `+0x404` data. FIRM gives up after 1,000,000 polls |
| `0x400D0020`, `0x400D0040`, `0x400D0060` | self-clearing bit | Reset bit 31 of three identical channels. The block's handler is on IRQ 36 |
| `0x400D1010` | self-clearing bit | Coefficient port: bit 31 go/busy, bit 30 write, low 12 bits index, `+0x14` and `+0x18` data. The page takes 853 writes during boot |

## What is left

* **PMU register file.** The 8-bit registers behind the bus hold what was written and start at 0. Real reset values, the charger, battery ADC and power-key bits are unknown, so FIRM sees no charger and no key.
* **PMU wake-up timer.** Nothing programs IRQ 48 by itself. A test has to raise it.
* **Bluetooth.** FIRM touches no baseband or radio register before it sleeps, so link-layer and radio blocks are untested. The 142 registers written through `0x40009000` are stored, not interpreted.
* **Audio.** `0x40097000`, `0x400D0000` and `0x400D1000` take their configuration and nothing clocks samples in or out. No DMA, no codec interrupts.
* **GPIO.** `0x40081000` reads back writes. No pin input, so in-ear, touch and case detection never change.
* **Sensors.** The I2C bus NACKs every address. A slave object can be attached through `I2CMaster.devices`.
* **Flash controller.** The JEDEC ID is a guess. Completion interrupts are raised but FIRM polls instead. Status-register protection bits are stored, not enforced.
* **Timing.** One instruction is one cycle. Flash, PLL lock, I2C and PMU transfers complete at once.
* **OTAP.** OTAP has not been booted on this model. [`otap_check.py`](../../openhuilian/emu/otap_check.py) still uses its own flash model.
* **h3emu and the patch checks** do not use the model yet.
