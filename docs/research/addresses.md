# Address index

This table collects the named function and data locations in the firmware sources. Addresses refer to H3Pro Max3 `2607061716` unless the role explicitly names a comparison build or loader.

## Address conventions

The table is sorted by program in alphabetical order, then by numeric address. Bare addresses are CPU addresses. `flash` marks physical flash offsets, and `FIRM+` marks offsets within a FIRM partition.

BOOT also groups the vendor boot-loader destinations, while OTAP groups the separate `zero_ota.bin` service-image vectors. Those rows name their actual image and do not establish H3Pro compatibility. Hardware register ranges are grouped with FIRM, which uses them.

## Consolidated table

| Address | Program | Name or role | Page |
|---|---|---|---|
| flash `0x000000` | BOOT | HLKJ header, bootloader and config area through `0x3000` | [Boot header](memory-map-and-boot.md#hlkj-boot-header) |
| flash `0x00001D` | BOOT | Flash-class configuration byte | [Flash class](memory-map-and-boot.md#flash-class-configuration) |
| flash `0x00005C` | BOOT | Flash-class configuration byte | [Flash class](memory-map-and-boot.md#flash-class-configuration) |
| flash `0x00005D` | BOOT | Flash-class configuration byte | [Flash class](memory-map-and-boot.md#flash-class-configuration) |
| flash `0x000060` | BOOT | Bootloader vector table | [Boot header](memory-map-and-boot.md#hlkj-boot-header) |
| flash `0x003000` | BOOT | Partition index | [Flash layout](memory-map-and-boot.md#flash-layout) |
| `0x810040` | BOOT | SL6806 `mp_uart_6806.bin[1088:]` loader destination | [UART loaders](uart-boot-rom.md#loader-sequence) |
| `0x850000` | BOOT | SL6801 `cal_frequent_drift_gyro_ur.bin[1088:]` loader destination | [UART loaders](uart-boot-rom.md#loader-sequence) |
| `0x860000` to `0x861CF0` | BOOT | Bootloader RAM image | [Address spaces](memory-map-and-boot.md#cpu-and-address-spaces) |
| `0x860101` | BOOT | Reset vector, Thumb bit set | [Boot header](memory-map-and-boot.md#hlkj-boot-header) |
| `0x860168` | BOOT | `FUN_00860168`, main | [Boot selection](memory-map-and-boot.md#boot-selection) |
| `0x8605F2` | BOOT | `FUN_008605f2`, download-mode strap check | [Boot selection](memory-map-and-boot.md#boot-selection) |
| `0x860E70` | BOOT | Read index, select OTAP/FIRM, copy and jump | [Boot selection](memory-map-and-boot.md#boot-selection) |
| `0x874000` | BOOT | SL6806 `mp_uart_6806.bin[0:1024]` loader destination | [UART loaders](uart-boot-rom.md#loader-sequence) |
| `0x878DF0` | BOOT | Initial stack pointer | [Boot header](memory-map-and-boot.md#hlkj-boot-header) |
| flash `0x004000` | FIRM | FIRM partition, XIP alias `0xC04000` | [Flash layout](memory-map-and-boot.md#flash-layout) |
| flash `0x04A9E0` | FIRM | XOR `0x59` identity-table start | [Identity](airpods-layer.md#identity-data) |
| flash `0x04BF58` | FIRM | Continuity advert template | [Adverts](airpods-layer.md#continuity-adverts) |
| FIRM+`0x55000` to `0x55930` | FIRM | h2sturbo `2506281656` SDP region | [SDP/HID](airpods-layer.md#sdp-and-hid-descriptors) |
| FIRM+`0x591E0` | FIRM | Compared h2sturbo builds' Continuity template | [Adverts](airpods-layer.md#continuity-adverts) |
| FIRM+`0x64A1A` | FIRM | Verified `decimate` patch literal, stock 3 | [Patch offsets](audio-and-dsp.md#verified-patch-offsets) |
| FIRM+`0x64C74` | FIRM | Verified `alpha` patch literal, stock 0.1 | [Patch offsets](audio-and-dsp.md#verified-patch-offsets) |
| FIRM+`0x96AA0` to `0x96AC4` | FIRM | h2sturbo ANC AT dispatch table | [ANC controls](audio-and-dsp.md#factory-anc-controls) |
| FIRM+`0xA7550` | FIRM | Verified `tx_ms` patch literal, stock 40 | [Patch offsets](audio-and-dsp.md#verified-patch-offsets) |
| flash `0x0AE000` | FIRM | SENC partition | [SENC](audio-and-dsp.md#senc-reader) |
| flash `0x0AF000` | FIRM | TONE partition | [Flash layout](memory-map-and-boot.md#flash-layout) |
| flash `0x0C4000` | FIRM | EQ2P partition | [EQ2P](audio-and-dsp.md#h3pro-eq2p-layout) |
| flash `0x0FC000` | FIRM | PSMP store | [NV API](settings-store.md#nv-api) |
| `0x7FFE14` | FIRM | Image base for the h2sturbo ANC-handler mapping | [ANC controls](audio-and-dsp.md#factory-anc-controls) |
| `0x800000` upward | FIRM | SRAM base, shared address space | [Address spaces](memory-map-and-boot.md#cpu-and-address-spaces) |
| `0x804C40` to `0x805C40` | FIRM | RAM hot code and vectors | [Address spaces](memory-map-and-boot.md#cpu-and-address-spaces) |
| `0x804C41` | FIRM | Partition entry, Thumb bit set | [Partition header](memory-map-and-boot.md#the-0x30-byte-partition-header) |
| `0x8052A0` | FIRM | `main`, creates `task main` | [Tasks](firm-runtime.md#tasks-and-timers) |
| `0x805444` | FIRM | `FUN_00805444`, partition lookup by tag | [Flash access](firm-runtime.md#flash-and-partition-access) |
| `0x80576C` | FIRM | `FUN_0080576c`, flash read | [Flash access](firm-runtime.md#flash-and-partition-access) |
| `0x805C40` to `0x82CA2C` | FIRM | Initialized data, then BSS toward stack | [Address spaces](memory-map-and-boot.md#cpu-and-address-spaces) |
| `0x812144` | FIRM | `FUN_00812144`, post event with payload | [Event bus](firm-runtime.md#event-bus) |
| `0x81232E` | FIRM | `FUN_0081232e`, event post without payload | [Event bus](firm-runtime.md#event-bus) |
| `0x81234C` | FIRM | `FUN_0081234c`, event post without payload | [Event bus](firm-runtime.md#event-bus) |
| `0x824B24` | FIRM | `FUN_00824b24`, master/slave role | [C0 routing](command-channel.md#c0-framing-and-routing) |
| `0x827564` | FIRM | `FUN_00827564`, module dispatch | [Modules](firm-runtime.md#module-dispatch) |
| `0x827591` | FIRM | PendSV vector target | [Tasks](firm-runtime.md#tasks-and-timers) |
| `0x8286A0` | FIRM | `FUN_008286a0`, flash write | [Flash access](firm-runtime.md#flash-and-partition-access) |
| `0x829600` | FIRM | `FUN_00829600`, milliseconds conversion | [Timers](firm-runtime.md#tasks-and-timers) |
| `0x829850` | FIRM | `FUN_00829850`, task creation | [Tasks](firm-runtime.md#tasks-and-timers) |
| `0x829A00` | FIRM | Scheduler start | [Tasks](firm-runtime.md#tasks-and-timers) |
| `0x82D3A0` | FIRM | `DAT_0082d3a0`, one-byte mode read/written by `52/62` | [C0 part 2](command-channel.md#c0-handler-part-2) |
| `0x82DB5C` | FIRM | Empty orientation-filter plugin slot | [Head tracking](airpods-layer.md#head-tracking) |
| `0x831E7C` | FIRM | Nine-entry module-handler table | [Modules](firm-runtime.md#module-dispatch) |
| `0x831EFC` | FIRM | RAM partition-index count | [Flash access](firm-runtime.md#flash-and-partition-access) |
| `0x831F1C` | FIRM | RAM partition-index entries | [Flash access](firm-runtime.md#flash-and-partition-access) |
| `0x833D1C` | FIRM | Three Euler angles in integer degrees | [Head tracking](airpods-layer.md#head-tracking) |
| `0x834305` | FIRM | Second live byte persisted as `anc_mode_sel` | [Settings](settings-store.md#setting-semantics) |
| `0x834306` | FIRM | Third live byte persisted as `anc_mode_sel` | [Settings](settings-store.md#setting-semantics) |
| `0x834307` | FIRM | First live byte persisted as `anc_mode_sel` | [Settings](settings-store.md#setting-semantics) |
| `0x879820` | FIRM | Stack top | [Address spaces](memory-map-and-boot.md#cpu-and-address-spaces) |
| `0x896744` to `0x8968B2` | FIRM | h2sturbo ANC AT handlers | [ANC controls](audio-and-dsp.md#factory-anc-controls) |
| `0xC00000` upward | FIRM | Flash XIP window, shared mapping | [Address spaces](memory-map-and-boot.md#cpu-and-address-spaces) |
| `0xC04000` | FIRM | FIRM XIP partition start | [Address spaces](memory-map-and-boot.md#cpu-and-address-spaces) |
| `0xC2AB6C` | FIRM | `FUN_00c2ab6c`, second module dispatch API | [Modules](firm-runtime.md#module-dispatch) |
| `0xC30032` | FIRM | `rom-read` patch stub in zero-filled dead space, FIRM+`0x2C032` | [ROM read](rom-read.md#how-it-works) |
| `0xC33BE8` | FIRM | Likely DRC/compressor threshold ladder | [DSP tables](audio-and-dsp.md#compiled-dsp-tables) |
| `0xC33C04` | FIRM | Likely DRC/compressor threshold ladder | [DSP tables](audio-and-dsp.md#compiled-dsp-tables) |
| `0xC33C8C` | FIRM | Likely DRC/compressor threshold ladder | [DSP tables](audio-and-dsp.md#compiled-dsp-tables) |
| `0xC33D14` | FIRM | Likely DRC/compressor threshold ladder | [DSP tables](audio-and-dsp.md#compiled-dsp-tables) |
| `0xC33D9C` | FIRM | Filter/DSP configuration block | [DSP tables](audio-and-dsp.md#compiled-dsp-tables) |
| `0xC34450` | FIRM | IMU setup table | [Head tracking](airpods-layer.md#head-tracking) |
| `0xC451F4` | FIRM | Standard reflected CRC32 table | [NV API](settings-store.md#nv-api) |
| `0xC4A9E0` to `0xC4BC80` | FIRM | XOR `0x59` Apple identity table | [Identity](airpods-layer.md#identity-data) |
| `0xC4BF58` | FIRM | Continuity advert template | [Adverts](airpods-layer.md#continuity-adverts) |
| `0xC4BFC6` | FIRM | AES S-box | [AES](airpods-layer.md#software-aes) |
| `0xC4C0E7` | FIRM | Second AES table | [AES](airpods-layer.md#software-aes) |
| `0xC4E68C` | FIRM | `FUN_00c4e68c`, dispatcher fallthrough and peer event forwarding | [Event bus](firm-runtime.md#event-bus) |
| `0xC4EBD4` | FIRM | `FUN_00c4ebd4`, OTA peer-entry retries | [OTA entry](command-channel.md#entering-ota-from-firm) |
| `0xC4ECC4` | FIRM | `FUN_00c4ecc4`, `55AA 80` handling | [OTA entry](command-channel.md#entering-ota-from-firm) |
| `0xC4F014` | FIRM | `FUN_00c4f014`, factory-reset path | [Text console](command-channel.md#receive-demux-and-text-console) |
| `0xC4F0CC` | FIRM | `FUN_00c4f0cc`, SPP/UART demux and `+test=` console | [Text console](command-channel.md#receive-demux-and-text-console) |
| `0xC4FBC0` | FIRM | `FUN_00c4fbc0`, main event dispatcher | [Event bus](firm-runtime.md#event-bus) |
| `0xC51418` | FIRM | `FUN_00c51418`, ANC prompt map | [Settings](settings-store.md#setting-semantics) |
| `0xC51578` | FIRM | `FUN_00c51578`, boot EQ2P reader call | [EQ2P reader](audio-and-dsp.md#eq2p-reader) |
| `0xC521F0` | FIRM | `FUN_00c521f0`, audio init and EQ2P reader call region | [DSP tables](audio-and-dsp.md#compiled-dsp-tables) |
| `0xC52630` | FIRM | `FUN_00c52630`, EQ preset command block | [EQ2P reader](audio-and-dsp.md#eq2p-reader) |
| `0xC52E4C` | FIRM | `FUN_00c52e4c`, C0 handler part 2 | [C0 part 2](command-channel.md#c0-handler-part-2) |
| `0xC53260` | FIRM | `FUN_00c53260`, module-7 handler | [Modules](firm-runtime.md#module-dispatch) |
| `0xC538E4` | FIRM | `FUN_00c538e4`, three-byte battery status | [C0 part 2](command-channel.md#c0-handler-part-2) |
| `0xC54CC0` | FIRM | `FUN_00c54cc0`, AAP state-change broadcaster | [AAP services](airpods-layer.md#service-structure) |
| `0xC54DA8` | FIRM | `FUN_00c54da8`, module-4 service handler | [AAP services](airpods-layer.md#service-structure) |
| `0xC5522C` | FIRM | `FUN_00c5522c`, AirPods-layer shutdown | [OTA entry](command-channel.md#entering-ota-from-firm) |
| `0xC5896C` | FIRM | `FUN_00c5896c`, IMU setup | [Head tracking](airpods-layer.md#head-tracking) |
| `0xC589BC` | FIRM | `FUN_00c589bc`, IMU setup using table `0xC34450` | [Head tracking](airpods-layer.md#head-tracking) |
| `0xC58A5C` | FIRM | `FUN_00c58a5c`, IMU FIFO reads | [Head tracking](airpods-layer.md#head-tracking) |
| `0xC58BD4` | FIRM | `FUN_00c58bd4`, IMU setup | [Head tracking](airpods-layer.md#head-tracking) |
| `0xC59298` | FIRM | `FUN_00c59298`, `task motion` | [Head tracking](airpods-layer.md#head-tracking) |
| `0xC5C6B0` | FIRM | `FUN_00c5c6b0`, preset-switch EQ2P read | [EQ2P reader](audio-and-dsp.md#eq2p-reader) |
| `0xC602F8` | FIRM | `FUN_00c602f8`, ENC/sidetone toggle path | [Text console](command-channel.md#receive-demux-and-text-console) |
| `0xC60324` | FIRM | `FUN_00c60324`, ENC/sidetone toggle path | [Text console](command-channel.md#receive-demux-and-text-console) |
| `0xC604DC` | FIRM | `FUN_00c604dc`, audio context and DSP setup | [DSP tables](audio-and-dsp.md#compiled-dsp-tables) |
| `0xC65A10` | FIRM | `FUN_00c65a10`, SENC record application | [SENC](audio-and-dsp.md#senc-reader) |
| `0xC6739C` | FIRM | `FUN_00c6739c`, motion low-pass stages | [Head tracking](airpods-layer.md#head-tracking) |
| `0xC68284` | FIRM | `FUN_00c68284`, exponential smoother | [Head tracking](airpods-layer.md#head-tracking) |
| `0xC68600` | FIRM | `FUN_00c68600`, motion-level classifier | [Head tracking](airpods-layer.md#head-tracking) |
| `0xC68924` | FIRM | `FUN_00c68924`, per-entry orientation processing | [Head tracking](airpods-layer.md#head-tracking) |
| `0xC690E8` | FIRM | `FUN_00c690e8`, EQ2P profile/kind reader | [EQ2P reader](audio-and-dsp.md#eq2p-reader) |
| `0xC69870` | FIRM | `FUN_00c69870`, C0 reply sender | [C0 framing](command-channel.md#c0-framing-and-routing) |
| `0xC698C4` | FIRM | `FUN_00c698c4`, boot authorization check | [Authorization](command-channel.md#firmware-authorization) |
| `0xC69958` | FIRM | C0 auth step 1 handler | [Authorization](command-channel.md#firmware-authorization) |
| `0xC699A6` | FIRM | C0 auth step 2 handler | [Authorization](command-channel.md#firmware-authorization) |
| `0xC69B3C` | FIRM | `FUN_00c69b3c`, C0 handler part 1 | [C0 part 1](command-channel.md#c0-handler-part-1) |
| `0xC69D26` | FIRM | `C0 83` call to `FUN_0080576c` inside `FUN_00c69b3c`, rerouted by the `rom-read` patch, FIRM+`0x65D26` | [ROM read](rom-read.md#how-it-works) |
| `0xC6A60C` | FIRM | `FUN_00c6a60c`, six-byte AAP opcode `0x12` payload | [AAP opcodes](airpods-layer.md#aap-opcodes) |
| `0xC6AAC0` | FIRM | `FUN_00c6aac0`, factory-reset path | [Text console](command-channel.md#receive-demux-and-text-console) |
| `0xC6AD1C` | FIRM | `FUN_00c6ad1c`, set boot-to-OTAP flag | [Flag](memory-map-and-boot.md#the-0x55aa-flag) |
| `0xC6AD78` | FIRM | `FUN_00c6ad78`, set TWS peer address | [Text console](command-channel.md#receive-demux-and-text-console) |
| `0xC6AE2C` | FIRM | `FUN_00c6ae2c`, factory-reset path | [Text console](command-channel.md#receive-demux-and-text-console) |
| `0xC6BD90` | FIRM | `FUN_00c6bd90`, battery check for OTA entry | [OTA entry](command-channel.md#entering-ota-from-firm) |
| `0xC6CDF0` | FIRM | `FUN_00c6cdf0`, peer send | [Peer sync](firm-runtime.md#peer-sync) |
| `0xC6E768` | FIRM | `FUN_00c6e768`, NV read | [NV API](settings-store.md#nv-api) |
| `0xC6E77C` | FIRM | `FUN_00c6e77c`, NV write | [NV API](settings-store.md#nv-api) |
| `0xC6ED54` | FIRM | `FUN_00c6ed54`, NV compaction | [NV API](settings-store.md#nv-api) |
| `0xC7144C` | FIRM | `FUN_00c7144c`, LFSR scrambler | [Authorization](command-channel.md#firmware-authorization) |
| `0xC71492` | FIRM | `FUN_00c71492`, authorization scrambler entry | [Authorization](command-channel.md#firmware-authorization) |
| `0xC714AC` | FIRM | PSMP CRC32 accumulator | [NV API](settings-store.md#nv-api) |
| `0xC87724` | FIRM | `FUN_00c87724`, AAP sender with first byte `0x20` | [Peer AAP](airpods-layer.md#peer-aap-transport) |
| `0xC87760` | FIRM | `FUN_00c87760`, AAP sender with first byte `0x40` | [Peer AAP](airpods-layer.md#peer-aap-transport) |
| `0xC87798` | FIRM | `FUN_00c87798`, AAP sender with first byte `0x10` | [Peer AAP](airpods-layer.md#peer-aap-transport) |
| `0xC87834` | FIRM | `FUN_00c87834`, ear-to-ear AAP parser | [Peer AAP](airpods-layer.md#peer-aap-transport) |
| `0xC8B1C4` | FIRM | `FUN_00c8b1c4`, AAP `0x00` handler helper | [AAP opcodes](airpods-layer.md#aap-opcodes) |
| `0xC8DF50` | FIRM | `FUN_00c8df50`, drop Bluetooth links | [OTA entry](command-channel.md#entering-ota-from-firm) |
| `0xC97000` to `0xC9A000` | FIRM | RF calibration code | [Hardware](firm-runtime.md#hardware-blocks) |
| `0xC9E66C` | FIRM | `FUN_00c9e66c`, module registration | [Modules](firm-runtime.md#module-dispatch) |
| `0xCA32BC` | FIRM | `FUN_00ca32bc`, clock-gate driver | [Hardware](firm-runtime.md#hardware-blocks) |
| `0xCA47B4` | FIRM | `FUN_00ca47b4`, timer creation | [Timers](firm-runtime.md#tasks-and-timers) |
| `0xCA4BE0` | FIRM | `FUN_00ca4be0`, connection lookup/create | [AAP services](airpods-layer.md#service-structure) |
| `0xCA4C48` | FIRM | `FUN_00ca4c48`, connection lookup/create | [AAP services](airpods-layer.md#service-structure) |
| `0xCA4C6C` | FIRM | `FUN_00ca4c6c`, connection lookup/create | [AAP services](airpods-layer.md#service-structure) |
| `0xCA4D54` | FIRM | `FUN_00ca4d54`, AAP `0x09` freshness/battery path | [AAP opcodes](airpods-layer.md#aap-opcodes) |
| `0xCA503C` | FIRM | `FUN_00ca503c`, AAP session-open helper | [AAP opcodes](airpods-layer.md#aap-opcodes) |
| `0xCA5090` | FIRM | `FUN_00ca5090`, AAP `0x21` helper | [AAP opcodes](airpods-layer.md#aap-opcodes) |
| `0xCA5138` | FIRM | `FUN_00ca5138`, AAP `0x17` helper | [AAP opcodes](airpods-layer.md#aap-opcodes) |
| `0xCA53F8` | FIRM | `FUN_00ca53f8`, AAP `0x4F` helper | [AAP opcodes](airpods-layer.md#aap-opcodes) |
| `0xCA65B8` | FIRM | `FUN_00ca65b8`, battery-gated AAP `0x25` helper | [AAP opcodes](airpods-layer.md#aap-opcodes) |
| `0xCA65E8` | FIRM | `FUN_00ca65e8`, battery-gated AAP `0x26` helper | [AAP opcodes](airpods-layer.md#aap-opcodes) |
| `0xCA6618` | FIRM | `FUN_00ca6618`, battery-gated AAP `0x28` helper | [AAP opcodes](airpods-layer.md#aap-opcodes) |
| `0xCA6680` | FIRM | `FUN_00ca6680`, AAP `0x31` helper after AES | [AAP opcodes](airpods-layer.md#aap-opcodes) |
| `0xCA6900` | FIRM | `FUN_00ca6900`, disconnect confirmation | [AAP services](airpods-layer.md#service-structure) |
| `0xCA696E` | FIRM | `FUN_00ca696e`, connect confirmation | [AAP services](airpods-layer.md#service-structure) |
| `0xCA738C` | FIRM | `FUN_00ca738c`, cleanup | [AAP services](airpods-layer.md#service-structure) |
| `0xCA73D2` | FIRM | `FUN_00ca73d2`, disconnect indication | [AAP services](airpods-layer.md#service-structure) |
| `0xCA761C` | FIRM | `FUN_00ca761c`, AAP `0x22` state-dependent helper | [AAP opcodes](airpods-layer.md#aap-opcodes) |
| `0xCA78B4` | FIRM | `FUN_00ca78b4`, AAP `0x17` helper | [AAP opcodes](airpods-layer.md#aap-opcodes) |
| `0xCA7E74` | FIRM | `FUN_00ca7e74`, AAP `0x09/0x0D` helper | [AAP opcodes](airpods-layer.md#aap-opcodes) |
| `0xCA80A8` | FIRM | `FUN_00ca80a8`, AAP `0x09/0x10` helper | [AAP opcodes](airpods-layer.md#aap-opcodes) |
| `0xCA80D0` | FIRM | `FUN_00ca80d0`, AAP `0x10` helper | [AAP opcodes](airpods-layer.md#aap-opcodes) |
| `0xCA832C` | FIRM | `FUN_00ca832c`, connect indication | [AAP services](airpods-layer.md#service-structure) |
| `0xCA879C` | FIRM | `FUN_00ca879c`, AAP `0x4D` helper | [AAP opcodes](airpods-layer.md#aap-opcodes) |
| `0xCA87D4` | FIRM | `FUN_00ca87d4`, AAP wire opcode switch | [AAP opcodes](airpods-layer.md#aap-opcodes) |
| `0xCA8BB8` | FIRM | `DAT_00ca8bb8`, remembered connection for AAP `0x21` | [AAP opcodes](airpods-layer.md#aap-opcodes) |
| `0xCA8BC0` | FIRM | `FUN_00ca8bc0`, L2CAP data indication | [AAP services](airpods-layer.md#service-structure) |
| `0xCA8C04` | FIRM | `FUN_00ca8c04`, L2CAP event dispatcher | [AAP services](airpods-layer.md#service-structure) |
| `0xCA90A4` | FIRM | `FUN_00ca90a4`, AAP `0x22` state check | [AAP opcodes](airpods-layer.md#aap-opcodes) |
| `0xCA910C` | FIRM | `FUN_00ca910c`, AAP `0x22` state check | [AAP opcodes](airpods-layer.md#aap-opcodes) |
| `0xCA928C` | FIRM | `FUN_00ca928c`, AAP `0x4D` helper | [AAP opcodes](airpods-layer.md#aap-opcodes) |
| `0xCA9370` | FIRM | `FUN_00ca9370`, AAP `0x09/0x12` helper | [AAP opcodes](airpods-layer.md#aap-opcodes) |
| `0xCA953C` | FIRM | `FUN_00ca953c`, shared AAP state setter | [AAP opcodes](airpods-layer.md#aap-opcodes) |
| `0xCA9610` | FIRM | `FUN_00ca9610`, AAP `0x26` setter | [AAP opcodes](airpods-layer.md#aap-opcodes) |
| `0xCA9624` | FIRM | `FUN_00ca9624`, AAP `0x28` setter | [AAP opcodes](airpods-layer.md#aap-opcodes) |
| `0xCA9688` | FIRM | `FUN_00ca9688`, AAP `0x39` setter | [AAP opcodes](airpods-layer.md#aap-opcodes) |
| `0xCA9C84` | FIRM | `FUN_00ca9c84`, AES advert caller | [AES](airpods-layer.md#software-aes) |
| `0xCA9F08` | FIRM | `FUN_00ca9f08`, AAP `0x31` AES entry | [AES](airpods-layer.md#software-aes) |
| `0xCA9F4C` | FIRM | `FUN_00ca9f4c`, AES advert caller | [AES](airpods-layer.md#software-aes) |
| `0xCAAAB0` | FIRM | `FUN_00caaab0`, quaternion/HID transmit callback | [Head tracking](airpods-layer.md#head-tracking) |
| `0xCAB53C` | FIRM | `FUN_00cab53c`, 40 ms motion transmit timer | [Head tracking](airpods-layer.md#head-tracking) |
| `0xCAB8D8` | FIRM | `FUN_00cab8d8`, AES advert caller | [AES](airpods-layer.md#software-aes) |
| `0xCAB92C` | FIRM | `FUN_00cab92c`, Continuity advert builder | [Adverts](airpods-layer.md#continuity-adverts) |
| `0xCABE28` | FIRM | `FUN_00cabe28`, AAP connection state machine | [AAP services](airpods-layer.md#service-structure) |
| `0xCAC106` | FIRM | `FUN_00cac106`, AddRoundKey-style loop | [AES](airpods-layer.md#software-aes) |
| `0xCAC12E` | FIRM | `FUN_00cac12e`, AES `xtime` | [AES](airpods-layer.md#software-aes) |
| `0xCAC140` | FIRM | `FUN_00cac140`, SubBytes/mix step | [AES](airpods-layer.md#software-aes) |
| `0xCAC1B8` | FIRM | `FUN_00cac1b8`, 336-byte key schedule | [AES](airpods-layer.md#software-aes) |
| `0x40000000` | FIRM | PMU, power and reset registers | [Hardware](firm-runtime.md#hardware-blocks) |
| `0x40009000` | FIRM | SYSCTRL | [Hardware](firm-runtime.md#hardware-blocks) |
| `0x40009134` to `0x400092B8` | FIRM | Peripheral clock gates and dividers | [Hardware](firm-runtime.md#hardware-blocks) |
| `0x40030000` | FIRM | Bluetooth baseband/BLE block | [Hardware](firm-runtime.md#hardware-blocks) |
| `0x40036000` | FIRM | RF calibration block | [Hardware](firm-runtime.md#hardware-blocks) |
| `0x40037000` | FIRM | Bluetooth baseband/BLE block | [Hardware](firm-runtime.md#hardware-blocks) |
| `0x40038000` | FIRM | Bluetooth baseband/BLE block | [Hardware](firm-runtime.md#hardware-blocks) |
| `0x40097000` | FIRM | Audio I2S/TDM block | [Hardware](firm-runtime.md#hardware-blocks) |
| `0xE000Exxx` | FIRM | Cortex-M SCB/NVIC range | [Hardware](firm-runtime.md#hardware-blocks) |
| `0xE000ED00` | FIRM | System Control Block | [Hardware](firm-runtime.md#hardware-blocks) |
| flash `0x0D2000` | OTAP | OTAP partition | [Flash layout](memory-map-and-boot.md#flash-layout) |
| flash `0x0FB000` | OTAP | Computed boot-to-OTAP flag page | [Flag](memory-map-and-boot.md#the-0x55aa-flag) |
| `0x804800` upward | OTAP | RAM-linked updater | [Address spaces](memory-map-and-boot.md#cpu-and-address-spaces) |
| `0x804C41` | OTAP | Separate `zero_ota.bin` entry, same RAM-entry convention | [Service image](images-and-variants.md#zero_otabin) |
| `0x809600` | OTAP | `OTAPPSMP` tag string | [Index handling](updater-otap.md#data-crc-and-index-handling) |
| `0x80E4C0` | OTAP | Erase routine for `82` | [Function map](updater-otap.md#function-map) |
| `0x80E538` | OTAP | Final CRC over index and payload | [Function map](updater-otap.md#function-map) |
| `0x80E5B8` | OTAP | Write index page | [Function map](updater-otap.md#function-map) |
| `0x80E622` | OTAP | Preserve OTAP/PSMP index records | [Function map](updater-otap.md#function-map) |
| `0x80E6B8` | OTAP | Preserve OTAP/PSMP index records | [Function map](updater-otap.md#function-map) |
| `0x80E730` | OTAP | Bootloader/config guard CRC | [Function map](updater-otap.md#function-map) |
| `0x80E770` | OTAP | `FUN_0080e770`, OTA state machine | [State machine](updater-otap.md#state-machine) |
| `0x80FE80` | OTAP | `FUN_0080fe80`, clear the OTA flag | [Function map](updater-otap.md#function-map) |
| `0x810914` | OTAP | `FUN_00810914`, C0 dispatcher | [OTAP C0](updater-otap.md#otap-mode-c0-commands) |
| `0x810CE0` | OTAP | `PTR_DAT_00810ce0`, auth-enabled flag pointer | [OTAP C0](updater-otap.md#otap-mode-c0-commands) |
| `0x819FD4` | OTAP | `FUN_00819fd4`, linked-master check | [Finalize and leave](updater-otap.md#finalize-leave-and-failure) |
| `0x82BCA4` | OTAP | CRC16 byte helper | [Function map](updater-otap.md#function-map) |
| `0x82BCC8` | OTAP | CRC16 buffer helper | [Function map](updater-otap.md#function-map) |
| `0x82BD48` | OTAP | Flash page write | [Function map](updater-otap.md#function-map) |
| `0x82BD9C` | OTAP | Flash erase | [Function map](updater-otap.md#function-map) |
| `0x86A4A4` | OTAP | Separate `zero_ota.bin` initial SP | [Service image](images-and-variants.md#zero_otabin) |
| `0x000000` upward | ROM | Mask-ROM address space | [ROM scope](mask-rom.md#call-surface-scope) |
| `0x0AA2` | ROM | `strlen` | [ROM entries](mask-rom.md#named-entries) |
| `0x0AB2` | ROM | `strcmp` | [ROM entries](mask-rom.md#named-entries) |
| `0x0B2A` | ROM | `memcpy` | [ROM entries](mask-rom.md#named-entries) |
| `0x0BAA` | ROM | `memset` | [ROM entries](mask-rom.md#named-entries) |
| `0x0C54` | ROM | `memcmp` | [ROM entries](mask-rom.md#named-entries) |
| `0x0C70` | ROM | `malloc` | [ROM entries](mask-rom.md#named-entries) |
| `0x0C74` | ROM | `free` | [ROM entries](mask-rom.md#named-entries) |
| `0x1A90` | ROM | Queue/event post | [ROM entries](mask-rom.md#named-entries) |
| `0x2A7C` | ROM | Timer/queue helper | [ROM entries](mask-rom.md#named-entries) |
| `0x83B4` | ROM | Flash read | [ROM entries](mask-rom.md#named-entries) |
| `0x9E3C` | ROM | RTOS helper used by task creation | [ROM entries](mask-rom.md#named-entries) |
| `0xB4F5` | ROM | SVC vector target | [ROM entries](mask-rom.md#named-entries) |
| `0xB514` | ROM | Flash write wrapper | [ROM entries](mask-rom.md#named-entries) |
| `0xB534` | ROM | Flash read wrapper | [ROM entries](mask-rom.md#named-entries) |
| `0xB5A9` | ROM | SysTick vector target | [ROM entries](mask-rom.md#named-entries) |
| `0xB6C4` | ROM | Exit critical section | [ROM entries](mask-rom.md#named-entries) |
| `0xB6D8` | ROM | Enter critical section | [ROM entries](mask-rom.md#named-entries) |
| `0xB78C` | ROM | Sleep N milliseconds | [ROM entries](mask-rom.md#named-entries) |
| `0xC096` | ROM | `printf` family | [ROM entries](mask-rom.md#named-entries) |
| `0xC0DC` | ROM | `printf` family | [ROM entries](mask-rom.md#named-entries) |
| `0x11000` to `0x31000` | ROM | Bluetooth stack call band | [ROM scope](mask-rom.md#call-surface-scope) |
| `0x11044` | ROM | Bluetooth host helper | [ROM entries](mask-rom.md#named-entries) |
| `0x110C0` | ROM | Bluetooth host helper | [ROM entries](mask-rom.md#named-entries) |
| `0x48268` | ROM | Flash helper | [ROM entries](mask-rom.md#named-entries) |
| `0x4B29C` | ROM | Bluetooth A2DP/RF helper | [ROM entries](mask-rom.md#named-entries) |
| `0x404132` | ROM | Audio/DSP helper | [ROM entries](mask-rom.md#named-entries) |
