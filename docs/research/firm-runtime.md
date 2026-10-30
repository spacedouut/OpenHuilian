# FIRM runtime

FIRM runs the normal Bluetooth, audio, sensor and app services on a small RTOS. Tasks communicate through a main event queue and a module dispatch table, with a separate transport for peer-bud state.

## Tasks and timers

The kernel core lives in mask ROM. SVC points to `0xB4F5` and SysTick to `0xB5A9`. PendSV points to RAM `0x827591`.

`main` at `0x8052A0` creates `task main`. `FUN_00829850(entry, arg, name, prio, stack)` creates tasks and `0x829A00` starts the scheduler.

| Task | Priority | Work |
|---|---|---|
| `task main` | 1 | Event loop and main dispatcher |
| `task btc`, `task bth`, `task bleh`, `bt_isr_bh`, `ble_isr_bh` | 9 / 9 / 7 / 19 | BT controller, host, BLE host and interrupt bottom halves |
| `bt audio server`, `amixer`, `tplayer`, `ain`, `audio ui` | 6 / 9 / 9 / 7 / 1 | A2DP/SCO sink, mixer, prompt player, mic input and UI sounds |
| `talk detect` | 8 | Voice activity, talk-through and sidetone gating |
| `tws process`, `tws_manager_task`, `tws_manager_mp_task` | 8 / 1 / 1 | Peer link and role management |
| `task motion`, `taskB motion` | 10 / 3 | IMU FIFO reads, sensor fusion, head tracking, tap and motion wake |
| `plxc_proximity_task`, `plxc_scan_task` | 2 / 1 | In-ear proximity |
| `sensor-hr` | 1 | VC30Fx heart-rate sensor |
| `task siri` | 6 | Voice-assistant trigger through `AT+BVRA` and `AT+APLSIRI` |
| `adc data`, `pmu_isr_bh`, `uart_isr_bh`, `spp_ota_bh` | 6 / 3 / 3 / 3 | Battery ADC, charger/PMU events, UART console and SPP receive |

The BT task group lists four priority values for five names in the source. It does not separately assign a value to each interrupt bottom half.

Timers use `FUN_00ca47b4(&handle, name, ticks, callback, ?, periodic, arg)`. The unknown argument remains unidentified. `FUN_00829600(ms)` converts milliseconds.

| Timer names | Area |
|---|---|
| `SleepTimer`, `BtSniffTimer` | Power and Bluetooth |
| `otaStateTimer` | OTA entry and exit |
| `AncTimer`, `spaceSyncTimer`, `SeamlessTimer` | Audio and synchronization |
| `tws scan timeout`, `ble find full timeout` | Peer and BLE discovery |
| `motion detect`, `hr_s2` | Sensors |
| `air fit timer`, `air motion timer`, `air motion tx timer`, `air heartrate tx timer`, `air resp timer` | AirPods services |
| `ble air adv open timer`, `ble air adv close timer` | Advertising |
| `juplus restart timer`, `TestUiTimer` | Restart and test UI |

The [mask ROM table](mask-rom.md) includes allocation, strings, critical sections and sleep helpers.

## Event bus

`FUN_00812144(id, payload, len)` posts an event. `FUN_0081232e` and `FUN_0081234c` provide forms without payloads. `task main` hands each event to `FUN_00c4fbc0(ev)`.

| Event field | Meaning |
|---|---|
| `ev[0]` | Event ID |
| `ev[1]` | Payload length |
| `ev[2..]` | Payload |
| Top byte of ID | Source family |

| ID family or ID | Source or meaning |
|---|---|
| `0x50xxxxxx` | Key and touch events |
| `0x80xxxxxx`, `0x81xxxxxx` | BT link state |
| `0x81000024` | Power-off request |
| `0xB0xxxxxx`, `0xB2xxxxxx` | Audio and HFP state |
| `0xC0300021` | A2DP/SCO link usage |
| `0xC1xxxxxx` | Charger and VBUS |
| `0xC1000004` | Carries `vbus_print` |
| `0xD0xxxxxx`, `0xD1xxxxxx`, `0xD2xxxxxx`, `0xD3xxxxxx` | BT host, pairing and TWS link |
| `0xD0000027` | ANC set from app |
| `0xD000002E` | ANC mode change |
| `0xF2xxxxxx`, `0xF3xxxxxx` | Audio mode |
| `0xF2000018` | Game-mode toggle |
| `0xF3000002` | EQ change |
| `0xF4000001` to `0xF4000005` | Factory ANC test and gains in the h2sturbo AT parser |
| `0xF6xxxxxx` | App protocol |
| `0xF600000E` | Likely a second app event related to OTA entry |
| `0xF600000F` | Enter OTA, payload byte 1 |
| `0xF6000046` | Re-enter OTA after slave handshake |
| `0xF7xxxxxx` | App session |
| `0xF7000001` | App authorized |
| `0xF7000002`, `0xF7000003` | Settings changed |

The following concrete IDs appear in the main dispatcher's literal-pool comparisons. A family label does not establish the exact meaning of each member.

| Family | Concrete dispatcher IDs |
|---|---|
| BT link | `0x80000019`, `0x80000020`, `0x80000016`, `0x80000017`, `0x80010016`, `0x80010017`, `0x8100003A` |
| Audio and HFP | `0xB0000010`, `0xB0000013`, `0xB2000001`, `0xB2000002`, `0xB2000003` |
| Link usage | `0xC0300021` |
| Charger | `0xC1000001`, `0xC1000004` |
| Host and pairing | `0xD000000B`, `0xD000001B`, `0xD000002B`, `0xD000002E`, `0xD1000001` |
| TWS link, `0xD20000xx` | `0xD2000001`, `0xD2000002`, `0xD2000007`, `0xD2000008`, `0xD2000009`, `0xD200000E` |
| Audio mode | `0xF2000011`, `0xF2000017` |
| App protocol | `0xF600000E`, `0xF600000F`, `0xF6000046` |
| App settings | `0xF7000003` |

Unrecognized IDs fall through to `FUN_00c4e68c`. It handles other Bluetooth and audio events and forwards some to the peer with opcode `0x20`.

## Module dispatch

`FUN_00827564(module, 0, type, len, data)` posts a buffer to a module. `FUN_00c2ab6c` is another dispatch API over the same nine-entry table at RAM `0x831E7C`.

Modules register through `FUN_00c9e66c(handler, module)`. A raw-BL scan identifies eight registration calls. The decompiler shows only three.

| Module | Role | Handler or registration |
|---|---|---|
| 1 | Bluetooth host | Registered twice |
| 2 | NV/PSM | Registered |
| 3 | Unidentified | Registered |
| 4 | AirPods/AAP services | `FUN_00c54da8` |
| 5 | Unidentified | Registered |
| 6 | Audio | Registered |
| 7 | SPP/UART transport | `FUN_00c53260` |

Module 7 uses type 1 for `05` frames, type 2 for `55AA` frames and type 3 for outgoing replies. Its case 0 reaches the second [C0 handler](command-channel.md#c0-handler-part-2).

Module 4 has about 40 internal service types. They cover state getters, NV reads and writes for `air_link`, `air_adv_key`, `air_pair`, `air_reset`, `air_clean`, `air_phone_addr`, `air_en` and serials, plus battery and peer relays. These service types are distinct from the [AAP wire opcode table](airpods-layer.md#aap-opcodes).

## Flash and partition access

| Address | Function or data | Behavior |
|---|---|---|
| `0x805444` | `FUN_00805444(name, &len)` | Look up a four-letter partition tag and return its flash address and length |
| `0x80576C` | `FUN_0080576c(dst, addr, len)` | Read flash |
| `0x8286A0` | `FUN_008286a0(src, addr, len, 1, 0)` | Write flash |
| `0x831EFC` | RAM index count | Number of entries |
| `0x831F1C` | RAM index entries | 16-byte records with name, address and length |

FIRM uses these APIs for EQ2P presets, the flag after OTAP and `C0 83` flash reads. [Settings store](settings-store.md) covers the higher-level PSMP API.

## Peer sync

`FUN_00c6cdf0(opcode, data, len)` sends `opcode + bytes` to the other bud. Setting handlers usually store the value locally and relay it when running on the master.

| Peer opcode | Payload or role |
|---|---|
| `0x0E` | OTA entry coordination, also used by OTAP exit coordination |
| `0x15` | ANC state, four bytes |
| `0x18` | `air_en` |
| `0x19` | `sn_info` |
| `0x1A` | Mode set by `C0 62` |
| `0x1B` | Bluetooth address |
| `0x1F` | AirPods advert key |
| `0x20` | Forwarded events |
| `0x32` | Ear detection |
| `0x33`, `0x34`, `0x35` | One-byte settings written by `66`, `67`, `68` |
| `0x36`, `0x37` | Left and right long-press actions |
| `0x38`, `0x39` | Left and right double-tap actions |
| `0x3A` | One-byte EQ-related write from `C0 A0` |
| `0x3B` | Part of the reported `0x32` to `0x3C` settings range, exact meaning unspecified |
| `0x3C` | User EQ write |
| `0x40`, `0x41` | Left and right serial fields |
| `0x46` | OTA state |
| `0x4B`, `0x4C` | Link records in the general peer map |
| `0x4B` | Slave Euler angles every 200 ms in the head-tracking path |

The source assigns `0x4B` both to link records and to motion data. Whether these uses depend on another context or one label needs correction is unverified.

## Hardware blocks

| Address | Block | Evidence |
|---|---|---|
| `0x40000000` | PMU, power and reset | Boot, sleep and interrupt-state helpers |
| `0x40009000` | SYSCTRL, clock gates and dividers | `FUN_00ca32bc` |
| `0x40009134` to `0x400092B8` | Peripheral enable bits and dividers | Accessed by the clock driver |
| `0x40030000`, `0x40037000`, `0x40038000` | Bluetooth baseband and BLE | `task btc` and `task bleh` code |
| `0x40036000` | Radio | RF calibration code at `0xC97000` to `0xC9A000` accesses this block |
| `0x40097000` | Audio I2S/TDM | `6wire mode`, `bclk1 slot num`, `bclk1 slot width`, `LR1 pol`, `gpio cfg sd7` strings |
| `0xE000Exxx` | Cortex-M SCB/NVIC | Core system registers |
| `0xE000ED00` | System Control Block | Fault-handler accesses |

| Sensor | Identification |
|---|---|
| ST LSM6DSV16BX IMU | I2C address `0x6A`, expected `WHO_AM_I` value `0x71`. `6dsox` is the driver name |
| VC30Fx optical heart-rate sensor | `vc30fx_*` NV keys and `HeartRateService` |
| PLXC proximity sensor | In-ear detection tasks |

Factory audio commands include `AT+MICTEST=`, `AT+ANCTEST=`, `AT+ANCFFG=`, `AT+ANCFBG=`, `AT+ANCAG=` and `AT+ANCDG=`. See [audio and DSP](audio-and-dsp.md#factory-anc-controls) for message IDs, parser details and the limits of the H3Pro evidence.
