# BuggyBot KiCad Hardware Files

This folder contains the KiCad design files used for the BuggyBot senior capstone project.

The design is based on the Raspberry Pi Compute Module 5 IO Board and is being used as a reference for developing the custom BuggyBot PCB.

## Main Project Files

- `CM5IO.kicad_pro`  
  Main KiCad project file. Open this file first to load the complete project.

- `CM5IO.kicad_sch`  
  Main schematic for the CM5 IO Board.

- `CM5IO.kicad_pcb`  
  PCB layout for the CM5 IO Board.

- `CM5IO.kicad_sym`  
  Custom symbol library used by the project.

## Additional Schematic Sheets

- `CM5_GPIO.kicad_sch`  
  GPIO-related circuitry.

- `CM5_HighSpeed.kicad_sch`  
  High-speed interfaces and related circuitry.

- `PCIe-M2.kicad_sch`  
  PCIe and M.2 circuitry.

## Libraries

- `CM5IO.pretty/`  
  Custom KiCad footprint library.

- `CM5IO.3dshapes/`  
  3D models used by PCB footprints.

- `fp-lib-table`  
  KiCad footprint library configuration.

- `sym-lib-table`  
  KiCad symbol library configuration.

## Other Files

- `CM5IOBOM.txt`  
  Bill of Materials from the original CM5 IO Board design.

## Opening the Project

1. Install KiCad 9 or a compatible newer version.
2. Clone or download the BuggyBot repository.
3. Navigate to:

   `Hardware/BuggyBot KiCAD`

4. Open:

   `CM5IO.kicad_pro`

Opening the `.kicad_pro` file should load the schematic, PCB, and associated project libraries.

## Project Purpose

These files are being used as a reference while developing the custom PCB for BuggyBot.

The original CM5 IO Board contains some different hardware than BuggyBot requires. The team will use these design files to identify the CM5 support circuitry and interfaces that must be retained for the final BuggyBot PCB.
