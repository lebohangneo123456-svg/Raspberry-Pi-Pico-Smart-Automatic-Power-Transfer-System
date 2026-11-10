# Project notes and verification boundaries

## Firmware provenance
The shipped V1 `Firmware/main.py` was extracted directly from the embedded `FIRMWARE/PI_PICO_1/main.py` member of the supplied Proteus `.pdsprj` project. No V2–V5 experimental firmware is substituted.

## Evidence available
Four still images show the Pico, LCD, source switches, voltage dividers, two relay drivers and two separate load lamps. They depict `AUTO MAIN`, `TRANSFER...`, `MAN MAIN`, and `MAN NO SOURCE` states.

## Interpretation
In MANUAL MAIN mode, a healthy backup supply does **not** automatically energize the backup relay if MAIN is absent. `MAN NO SOURCE` with 0 V main and 12 V backup is consistent with the original firmware's manual-selection logic; it is not automatically proof of a circuit fault.

**Current limitation:** L1 and L2 are separate output indicators wired from RL1 and RL2. Their activation is not proof that one common physical load switches source. The controller is therefore documented as an ATS *prototype / source-selection demonstration* rather than a finished ATS.

## Missing evidence
Oscilloscope traces, actual end-to-end changeover timing, GPIO-to-relay contact correlation, power quality, load transfer on one shared load, overcurrent protection, and real hardware verification remain to be collected.

## Engineering precautions
Use only low-voltage simulation for now. Verify source isolation, correct relay contact mapping, proper coil driving, thermal limits, fuses, diode current capacity, and I²C pull-ups before any physical build.
