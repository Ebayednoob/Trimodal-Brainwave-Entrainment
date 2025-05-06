# Bio-Entrainment Therapeutics : Trimodal Brainwave Entrainment Devices

> **Bio-Entrainment Therapeutics currently holds provisionally Patents for the following:(Patent Pending)**<br>
```
> 1: Ein Sof Trimodal Brainwave Entrainment Device
> 2: Ein Sof Scalar Wave Quantum Communication Device
> 3: Bifilar Coil Hemispheric Entrainment Protocols for Hemi-Synch
```

Here we host a repository for the firmware, software, designs, and research documentation underpinning the **Ein Sof Device and Protocol**, a precision-engineered, trimodal brainwave entrainment apparatus that synergizes electromagnetic, auditory, and visual stimulation to facilitate hemispheric synchronization and explore protocols for quantum-communication via neuron based microtubule circuits.

```All Documntation, Research, Firmware, Software, Designs, Circuitry is offered under General licensing Understanding, and is not to be sold or reproduced with the intention of resale.```

---

## Table of Contents

1. [Introduction](#introduction)
2. [Theory of Operation](#theory-of-operation)

   * [Trimodal Entrainment Overview](#trimodal-entrainment-overview)
   * [Electromagnetic Modality](#electromagnetic-modality)
   * [Auditory Modality](#auditory-modality)
   * [Visual Modality](#visual-modality)
   * [Synergistic Effects](#synergistic-effects)
3. [Hardware Architecture](#hardware-architecture)

   * [Bifilar Toroidal Coil Design](#bifilar-toroidal-coil-design)
   * [Electromagnetic Driver Circuit](#electromagnetic-driver-circuit)
   * [Audio Transducer System](#audio-transducer-system)
   * [Visual Stimulus Module](#visual-stimulus-module)
4. [Software Architecture](#software-architecture)

   * [Signal Generation Engine](#signal-generation-engine)
   * [Control Interface](#control-interface)
   * [Communication Protocol](#communication-protocol)
5. [Installation and Setup](#installation-and-setup)

   * [Prerequisites](#prerequisites)
   * [Building the Firmware](#building-the-firmware)
   * [Installing the Software](#installing-the-software)
6. [Usage Guide](#usage-guide)

   * [Basic Operation](#basic-operation)
   * [Configuring Entrainment Protocols](#configuring-entrainment-protocols)
   * [Safety and Best Practices](#safety-and-best-practices)
7. [Calibration and Tuning](#calibration-and-tuning)

   * [Magnetic Field Calibration](#magnetic-field-calibration)
   * [Audio Frequency Calibration](#audio-frequency-calibration)
   * [Visual Pulse Calibration](#visual-pulse-calibration)
8. [Validation and Testing](#validation-and-testing)
9. [FAQ](#faq)
10. [Contributing](#contributing)
11. [License](#license)
12. [References](#references)
13. [Acknowledgements](#acknowledgements)

---

## Introduction

The **Ein Sof Device and Procedure** is a modular, licensed framework for exploring **trimodal brainwave entrainment**. 
By delivering precisely synchronized magnetic pulses, auditory binaural stimuli, and visual flicker patterns, that is controlled and modulated via Artificial Intelligence coupled with high resolution EEG Neurofeedback the device aims to:

* Induce and stabilize targeted EEG bandwidths (delta, theta, alpha, beta, gamma)
* Promote interhemispheric coherence
* Facilitate experimental scalar wave brainwave coupling

This repository contains all design files, schematics, firmware, control software, and theoretical background necessary to reproduce, modify, and extend the platform.

---

## Theory of Operation

### Trimodal Entrainment Overview

Trimodal entrainment fuses three stimulation streams, while utilizing proprietary algorithms to 
create and entrain specific, safe, and highly customized cymatic and oscillation patterns in neurons
utilizing the following:


1. **Electromagnetic (EM)** pulses via bifilar toroidal coils
2. **Electromagnetic (EM)** Frequency Modulation in the Microtubule Resonance Frequencies.
3. **Auditory** binaural beat generation
4. **Auditory** Iso-Chronic tone generation
5. **Auditory** Acoustic Coordinated Neuromodulation Reset 
6. **Visual** pulsed light sequences
7. **Visual** EDMR light sequences
8. **Meditative** Guided therapeutic sessions designed specifically for PTSD, Trauma, and Consciousness exploration.

Together, these modalities exploit cross‑modal resonance to amplify entrainment effects beyond what each could achieve in isolation.
The Ein Sof Project aims to bring accessability to these to provide a safe and repeatable experience while experimenting and combining these modalities.

### Electromagnetic Modality

* **Coil Geometry**: Bifilar toroid presenting a pulsed, bidirectional magnetic field to minimize net DC bias
* **Target Frequencies**: 1–40 Hz tested; primary focus on theta (4–8 Hz) and alpha (8–12 Hz)
* **Driver**: High‑precision MOSFET switching, generating <1 µs rise times

### Auditory Modality

* **Binaural, Isochronic, and Harmonic Entrainment Tones**: Perfectly Designed to induce brainwave coherence at |L–R| = target
* **Implementation**: Custom program with neurofeedback and real‑time waveform synthesis
* **Delivery**: Headphones or spatialized speaker array

### Visual Modality

* **Stimulus**: LED array, 650nm Biophotomodulation through polarization filters that compliment entrainment cymatic algorithms.
* **Parameters**: Duty cycle, luminance, and phase aligned to EM and auditory streams.
* **Synchronization**: µs‑level phase locking via shared clock.

### Synergistic Effects

Cross‑modality coupling exploits:

* **Cymatic Geometry**: Visual patterns reinforcing EM field geometries, along with entrainment tones for maximum immersion.
* **Audiomagnetic Resonance**: Sound‑driven vibrational modulation of coils with algorithmically synchronized timing.
* **Neurofeedback Loop**: Easy incorporation of custom EEG devices for real-time neuro-feedback for adaptive entrainment

---

## Hardware Architecture

### Bifilar Toroidal Coil Design

```!WARNING! MISUSE OR IMPROPER COIL DESIGN CAN LEAD TO FATAL INJURIES AND EVEN DEATH !WARNING!```
* **Specifications**:
Pre-requisites: Proprietary Algorithms designed through extensive research and experience designing RF antennas, amplifiers, and high end metrology equipment.
Design Specifications for the Toroidal Coil design are unique per individual. Each brain is different, Each head is different.

* **3D Model**: `/hardware/models/coil_3d.stl`

### Electromagnetic Driver Circuit

* Schematic: `/hardware/schematics/em_driver.sch`
* Bill of Materials: `/hardware/BOM/em_driver_bom.csv`
* Key components: STM32F407 MCU, IRLZ44N MOSFETs, high‑current H‑bridge

### Audio Transducer System

* Stereo DAC module: PCM5122 breakout
* Amplifier: TPA3118D2, 2×50 W
* Speaker/headphone jack wiring diagram in `/hardware/schematics/audio_out.sch`

### Visual Stimulus Module

* LED Array: WS2812B strip controlled via DMA
* Goggles variant: 4× high‑luminosity SMD LEDs per eye
* PCB: `/hardware/pcb/visual_driver.pcb`

---

## Software Architecture

### Signal Generation Engine

* Written in C for the STM32 platform
* Core modules:

  * `em_waveform.c` – generates pulse trains
  * `audio_waveform.c` – synthesizes binaural signals
  * `visual_waveform.c` – drives LED patterns

### Control Interface

* Host app in Python: `/software/control_app/`
* GUI built with PyQt5
* Real‑time telemetry over USB‑CDC

### Communication Protocol

* Custom binary framed protocol (64 bytes) for command, status, and EEG feedback
* Defined in `/software/protocol/spec.md`

---

## Installation and Setup

### Prerequisites

* **Hardware**: STM32F4 development board, MOSFET driver modules, DAC breakout, LED strip
* **Software**:

  * ARM GCC toolchain
  * Python 3.10+ with `pyqt5`, `pyserial`
  * `make`, `openocd` for flashing

### Building the Firmware

```bash
cd hardware/firmware
make all              # compile
make flash            # flash to STM32 via ST‑Link
```

### Installing the Software

```bash
cd software/control_app
git clone <repo-url>
pip install -r requirements.txt
python main.py        # launch control GUI
```

---

## Usage Guide

### Basic Operation

1. Power on the Ein Sof Device
2. Launch the Control App
3. Select desired entrainment protocol (preset or custom)
4. Click **Start** to initiate stimulation

### Configuring Entrainment Protocols

* Presets located in `/software/control_app/protocols/`
* Custom JSON definitions: see spec in `/software/control_app/README.md`

### Safety and Best Practices

* Limit single sessions to 20 minutes initially
* Ensure no metallic implants or pacemakers
* Operate in a distraction‑free environment

---

## Calibration and Tuning

### Magnetic Field Calibration

* Use a Gaussmeter to measure coil field strength at 10 cm
* Adjust driver current limit in `em_driver.c`

### Audio Frequency Calibration

* Verify ∆f accuracy with audio spectrum analyzer
* Tweak sample rate and buffer sizes in `audio_waveform.c`

### Visual Pulse Calibration

* Confirm duty cycle with photodiode + oscilloscope
* Modify PWM settings in `visual_waveform.c`

---

## Validation and Testing

* EEG recordings (10 channels) plotted alongside stimulation logs in `/validation/`
* Scripts for signal analysis in `/validation/analysis/`
* Example datasets: `/validation/data/`

---

## FAQ

**Q: Can I integrate EEG feedback?**
A: Yes—see `protocol/spec.md` for EEG frame definitions and `/software/control_app/ee
g_loop.py` for a demonstration.

**Q: Is wireless operation supported?**
A: Not in this release; future revisions will explore BLE and LoRa.

---

## Contributing

* Please open issues for bug reports and feature requests
* Submit pull requests against `develop` branch
* Adhere to existing code style and run `make format`

---

## License

This project is licensed under the **MIT License**, with the hardware covered by **Patent Pending** status. See [`LICENSE`](./LICENSE) for details.

---

## References

1. Hoard, G. & Static (2025). *Trimodal Brainwave Entrainment Methods for Quantum Consciousness Interfaces* (Provisionary Patent Application).
2. Valdes‑Sosa, P.A. et al. (2024). *Bifilar Toroidal Coil Effects on Human EEG*. Journal of Neuroengineering.
3. Oster, G. (1973). *Auditory Beats in the Brain*. Scientific American.

---

## Acknowledgements

* Special thanks to collaborators in Metrology Lab and Occult Research Group
* Inspiration from Nikola Tesla’s bifilar coil work and Enochian theurgy practices
* Tester community on Patreon and Neural Awakening channel

---
