# 14 · 52bluetooth.com forum survey

52bluetooth (`bbs.52bluetooth.com`) is the main Chinese Bluetooth-chip engineering forum. It was
searched with a logged-in account for anything Huilian / 377H3 / StarFun. Raw search results and
thread dumps: [`data/52bluetooth/`](../data/52bluetooth/) (`search.json` = search-term → hit list,
`t<tid>.txt` = thread text + attachment links). Helper: [`tools/bt52.py`](../tools/bt52.py)
(needs a browser session; it drives the logged-in Chrome via CDP).

## Result: nothing on 377H3 / H3Pro / StarFun — [confirmed]

Terms with **zero relevant hits**: `377H3`, `H3Pro`, `H3Pro Max3`, `377Youth`, `心动版`,
`StarFun`, `SL6801`, `SL6806`, `SmartLink 蓝牙`, `慧联 SDK`, `慧联 烧录`, `慧联 固件`,
`慧联 OTA升级`, `慧联 降噪/通透/透明模式`. `377` alone returns unrelated Qualcomm/Melexis parts.
The site has no Huilian sub-forum; Huilian content sits in "其他(BR/EDR综合讨论)" and is almost all
posted by one vendor account (`332316195`) plus one distributor (`278341399`).

## Huilian threads that exist

| Thread | Date | Content | Attachments |
|---|---|---|---|
| 有没有熟悉慧联方案的？介绍一下。 (tid 80375) | 2021-04 | user comparison: Huilian **A6** ANC deeper and lower floor-noise than Airoha 1562A; Airoha has app EQ, Huilian didn't (then) | none |
| 慧联检测软件 (tid 81492) | 2021-09 | "Huilian test software", unspecified | `慧联检测.rar` — **10 coins** |
| 慧联TWS200G封装及原理图 (tid 82288) | 2021-11 | TWS200G reference schematic, single-mic, touch key | `TWS200G_V1.1_20210926.zip` — **5 coins** |
| 慧联TWS200+陀螺仪原理图及PCB封装 (tid 84340) | 2022-06 | TWS200 + BMI160 gyro (spatial audio) | 2 × zip — **5 coins each** |
| 慧联TWS300头戴耳机空间音频方案 (tid 88862) | 2024-03 | TWS300 headset: BT5.4, LDAC/AAC/SBC, 32 ms game mode, QFN36 4×4 mm | inline images only |
| 慧联2.4G技术及其应用总览 / WS300 / 2.4G mics (tids 89590, 85864, 84687, 89052) | 2022–24 | 2.4 GHz dongle/mic product lines | some paid |
| AI ENC慧联M200 (tid 92241) | 2025-06 | M200: BT + 2.4G + USB + AI ENC | datasheet ~2 coins |

**Nothing was purchased.** The paid items are datasheets/schematics for older parts and a
2021 test utility of unknown scope; none plausibly contains 377H3 firmware, SDK, or OTA material,
and everything in [12](12-shenju-flasher.md)/[13](13-open-source-tooling.md) was more useful and
free. Product-name overlap (TWS300 / WS300A) between these "慧联" posts and Shenju's site
`shenjugroup.com` supports Huilian ≈ Shenju/SmartLink being one family — **[inferred]**.

## If someone wants to dig further

* Coin balance and per-attachment prices are visible on each thread once logged in; the
  `慧联检测.rar` (test tool) is the only item that might reveal a debug/AT protocol.
* Worth re-searching periodically: `377H3`, `H3 Pro`, `慧联 H3`, `StarFun 固件`.
