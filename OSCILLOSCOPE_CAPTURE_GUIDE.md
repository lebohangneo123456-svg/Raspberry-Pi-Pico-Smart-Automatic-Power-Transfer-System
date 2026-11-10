# Oscilloscope capture guide — Smart DC ATS (original V1 firmware)

These signals are **DC levels changing with switching events**, not AC sine waves or PWM. Record **real Proteus output**. Do not publish modeled/illustrative traces as measured results.

## Suggested 4-channel capture

| Channel | Probe placement | Approximate high reading | Expected transition |
|---|---|---:|---|
| A | Pico GP26 (main ADC input), against GND | 2.1 V (12 V input) | 2.1 V → 0 V when MAIN is disconnected |
| B | Pico GP27 (backup ADC input), against GND | 2.1 V (12 V input) | 0 V → 2.1 V when BACKUP is connected |
| C | Pico GP15 (Q1 input signal), against GND | 3.3 V logic HIGH | High on MAIN selection; low on outage/transfer |
| D | Pico GP16 (Q2 input signal), against GND | 3.3 V logic HIGH | High after BACKUP qualification and transfer gap |

Other useful measurements: RL1 coil voltage, RL2 coil voltage; voltage across each lamp; 7805's regulated 5 V output; Pico 3.3 V rail.

## Proteus scope setup

1. Place `OSCILLOSCOPE` (virtual instrument) and attach channels A/B/C/D to the four nodes above. Ensure common reference ground.
2. Select **DC coupling** for all channels. Start with approximately **1 V/div** for A/B and **1 V/div** for C/D; shift the trace position to place 0 V on-screen. Adjust if needed.
3. Start with **500 ms/div or 1 s/div** to capture the original V1 `RECOVERY_MS = 1500` and `DEAD_TIME_MS = 250` control delays. For detailed transfer edges, repeat with approximately **50–100 ms/div**.
4. Trigger on **Channel A falling edge** when MAIN is disconnected (if the scope supports edge triggering and pretrigger capture). Otherwise let the trace scroll and capture the event manually.
5. Begin with both supplies healthy in AUTO mode, open the MAIN source switch, then observe C falling and D rising following software qualification and break-before-make timing.
6. Restore MAIN and repeat. Save a screenshot that includes the scope scale controls and the signals.

Note: The supply voltage sensed by GP26/GP27 is ~2.1 V for a 12 V input because of the 47k/10k dividers. The main/backup GPIO high logic is nominally 3.3 V, not 12 V. The controller's measured delays can differ from configured values due to sampling, LCD traffic, event timing and simulation speed.

## Suggested filename and README embed (only after real capture)

`Images/05_zero_crossing_NOT_APPLICABLE.png` is **not** a suitable name; this is DC transfer, not AC zero-cross detection.

Prefer `Images/05_voltage_sensing_and_relay_commands.png` and embed with:

```markdown
![Actual Proteus capture of main/backup sensors and GPIO relay commands](Images/05_voltage_sensing_and_relay_commands.png)
```

Do not create this file until a real Proteus capture exists.
