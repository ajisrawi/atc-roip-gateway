# ATC RoIP Gateway — Firmware

ED-137-style Radio-over-IP firmware for the STM32H743 gateway board:
SIP session endpoint + RTP audio (G.711 µ-law @ 8 kHz) with the ED-137
Radio-profile RTP header extension carrying PTT and squelch (SQU), R2S-style
keepalives, TLV320AIC23B codec driver, and isolated PTT/COR radio signaling.
Two channels: **VHF = left**, **HF = right** audio channel.

```
firmware/
├── CMakeLists.txt            build (arm-none-eabi-gcc, CMake)
├── cmake/arm-none-eabi.cmake toolchain file
├── flash.ps1                 flash helper (STM32CubeProgrammer CLI)
├── src/
│   ├── main.c                init + superloop
│   ├── board.h               pin map (matches schematic rev A)
│   ├── app_config.h          network / codec / behaviour settings
│   ├── ed137/
│   │   ├── rtp_ed137.h/.c    RTP + ED-137 header ext (PTT type, SQU), R2S
│   │   ├── sip_mini.h/.c     minimal SIP UA (INVITE/ACK/BYE/OPTIONS + SDP)
│   │   └── g711.h/.c         µ-law encode/decode
│   ├── audio/
│   │   ├── aic23.h/.c        TLV320AIC23B register driver (I2C)
│   │   └── sai_stream.h/.c   SAI1 DMA double-buffer streaming
│   ├── net/
│   │   └── roip_chan.h/.c    per-radio channel: jitter buffer, PTT/COR logic
│   └── dsp/
│       └── voxagc.h/.c       HPF + AGC + VOX squelch (HF conditioning)
└── third_party/              (you fetch: STM32CubeH7 → HAL + lwIP + CMSIS)
```

## Dependencies (fetch once)

The application code is self-contained; it builds against ST's HAL, CMSIS and
lwIP from the official STM32CubeH7 package:

```bash
git clone --depth 1 https://github.com/STMicroelectronics/STM32CubeH7 third_party/STM32CubeH7
```

Toolchain: [Arm GNU Toolchain](https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads)
(`arm-none-eabi-gcc`) and CMake ≥ 3.20 — or open the tree in **STM32CubeIDE**
and add `src/` to a generated STM32H743VITx project (easiest route).

## Build

```bash
cmake -B build -DCMAKE_TOOLCHAIN_FILE=cmake/arm-none-eabi.cmake
cmake --build build
```

Produces `build/atc-roip-gw.elf` / `.bin` / `.hex`.

## Flash (two ways)

**1. SWD via ST-LINK on header J2** (3V3, SWDIO, SWCLK, GND, NRST):

```powershell
./flash.ps1            # uses STM32_Programmer_CLI, SWD
```

**2. USB-less DFU fallback: system bootloader over UART on J3**
(BOOT0 high at reset → STM32 bootloader; then):

```powershell
STM32_Programmer_CLI -c port=COMx br=115200 -w build/atc-roip-gw.bin 0x08000000 -v -rst
```

Install [STM32CubeProgrammer](https://www.st.com/en/development-tools/stm32cubeprog.html)
for `STM32_Programmer_CLI`.

## Configuration

Edit `src/app_config.h` (static IP / DHCP, peer address, SIP on/off, codec
G.711 vs pass-through, VOX thresholds), or use the UART console on J3
(115200 8N1) at runtime — type `help`.

## ED-137 compliance status

Implemented toward the **ED-137B Radio profile**: SIP INVITE/ACK/BYE/OPTIONS
with WG67-style SDP (`a=type:radio`), RTP/PCMU 8 kHz, RTP header extension
carrying PTT type + SQU + PTT-id, and periodic R2S-style keepalive while idle.
The exact bit numbering of the extension word and the WG67 SDP attribute set
MUST be verified against the licensed EUROCAE ED-137B/C text and a conformance
tool (e.g. GL MAPS ED-137) before claiming compliance — constants live in one
place (`rtp_ed137.h`) to make that adjustment trivial.
