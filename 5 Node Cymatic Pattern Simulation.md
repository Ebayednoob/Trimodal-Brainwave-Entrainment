# Cymatics Visualizer

A real-time interactive application for visualizing cymatics patterns and wave interference phenomena.

![Cymatics Visualizer](https://github.com/yourusername/cymatics-visualizer/raw/main/screenshots/main_interface.jpg)

## Overview

Cymatics Visualizer allows you to explore the fascinating patterns formed when sound waves interact. The application simulates how multiple sound sources create interference patterns similar to those observed in physical cymatics experiments, where particles on plates or liquids form geometric patterns in response to sound vibrations.

This tool is useful for:
- Education: Demonstrating wave physics, interference, and standing wave principles
- Sound design: Exploring relationships between audio frequencies and spatial patterns
- Art: Creating visual representations of sound relationships

## Features

- Interactive real-time visualization of interference patterns
- Control up to 5 sound sources with adjustable:
  - Position (drag and drop on the canvas)
  - Frequency (50Hz-5000Hz)
  - Amplitude
- Audio output of the combined sound sources
- Advanced distance analysis tools:
  - Distance Table: Shows mathematical relationships between sound sources
  - Distance Graph: Visualizes wavelength ratios between sources
  - Node Diagram: Maps the spatial relationships and resonance quality
- Intuitive controls for play, pause, and reset

## Installation

### Prerequisites

- Python 3.6+
- PyQt5
- NumPy
- PyQtGraph
- SoundDevice

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/cymatics-visualizer.git
cd cymatics-visualizer
```

2. Install dependencies:
```bash
pip install numpy pyqt5 pyqtgraph sounddevice
```

3. Run the application:
```bash
python cymatics_visualizer.py
```

## Usage Guide

### Main Interface

The application window is divided into two main sections:
- Left side: Visualization canvas displaying the interference pattern
- Right side: Control panel for adjusting sound source parameters

#### Basic Controls

1. **Sound Sources**: The visualization shows 5 movable sound sources (colored circles)
   - Drag these points to reposition them on the canvas
   - Each movement updates the interference pattern in real-time

2. **Frequency Controls**: For each sound source (1-5)
   - Slider: Quick adjustment of frequency (50Hz-5000Hz)
   - Spin box: Precise frequency input

3. **Amplitude Controls**: For each sound source (1-5)
   - Slider: Adjusts the relative strength of each source (0-100%)

4. **Control Buttons**:
   - Play: Start/resume the visualization and audio
   - Pause: Pause the visualization and audio
   - Reset: Return all sources to default positions and settings
   - Analyze Distances: Open the distance analysis window

### Distance Analyzer

The analyzer window provides deeper insights into the mathematical relationships between sound sources:

#### Distance Table Tab
Shows numerical data for each pair of sound sources:
- Distance: Physical separation between sources
- Wavelength Ratio: Distance as a multiple of average wavelength
- Standing Wave Node Count: Number of nodes in the standing wave between sources
- Resonance Quality: How well the distance creates resonance (higher is better)

#### Distance Graph Tab
Visual representation of wavelength ratios between source pairs:
- Bars show distance as a multiple of wavelength
- Green reference lines mark optimal ratios (0.5λ, 1.0λ, 1.5λ, 2.0λ)
- Color coding indicates resonance quality (green = good, red = poor)

#### Node Diagram Tab
Spatial map showing:
- Positions of all sound sources
- Lines connecting sources with wavelength ratio labels
- Color-coded connections based on resonance quality

## Theory and Applications

### Cymatics Principles

Cymatics is the study of visible sound and vibration patterns. When sound waves interact, they create:
- Constructive interference: Waves add together, creating areas of high amplitude
- Destructive interference: Waves cancel each other, creating areas of low amplitude

The resulting patterns depend on:
- Frequency relationships between sources
- Geometric arrangement of sources
- Phase relationships

### Optimal Arrangements

For the most visually striking patterns:
- Position sources at distances that are whole or half-multiples of wavelength
- Use frequency ratios based on simple fractions (1:2, 2:3, 3:4, etc.)
- Aim for high resonance quality values in the distance analyzer

### Practical Applications

- **Educational**: Demonstrate principles of wave physics, interference, and standing waves
- **Musical**: Explore relationships between musical intervals and visual patterns
- **Artistic**: Create visual compositions based on sound relationships
- **Sound Design**: Visualize spatial relationships in multi-speaker setups

## Troubleshooting

### Common Issues

- **No audio output**: The application will continue to work visually even if audio fails
- **Performance issues**: Reduce the window size or pause when not actively using
- **Unable to drag points**: Make sure you're clicking directly on the source circles

### System Requirements

- Runs best on systems with dedicated graphics
- Minimum 4GB RAM recommended
- CPU: Any modern dual-core processor or better

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Inspired by the work of Ernst Chladni and Hans Jenny in cymatics
- Built with PyQt5 and PyQtGraph for visualization
