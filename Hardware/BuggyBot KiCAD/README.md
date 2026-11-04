# BuggyBot KiCad Hardware Files

This folder contains the KiCad design files used for the BuggyBot senior capstone project.

The design started from the Raspberry Pi Compute Module 5 IO Board files and was modified into the custom BuggyBot carrier PCB. Abigail Duran completed the layout and generated the manufacturing files in Week 11 (11/03/2026), and Ethan Wells gave final approval to send it for manufacturing.

## Main Project Files

- `CM5IO.kicad_pro`  
  Main KiCad project file. Open this file first to load the complete project.

- `CM5IO.kicad_sch`  
  Main schematic, inherited from the CM5 IO Board.

- `CM5IO.kicad_pcb`  
  PCB layout for BuggyBot: 4 layers, 1.6 mm FR-4. Earlier layouts,
  including the 10/23 redesign file, are in Git history.

- `CM5IO.kicad_sym`  
  Custom symbol library used by the project.

## Additional Schematic Sheets

- `CM5_GPIO.kicad_sch`  
  GPIO-related circuitry, including the BuggyBot additions: 4-pin quick-connect
  ports for the IMU (J3) and the LCD (J4).

- `CM5_HighSpeed.kicad_sch`  
  High-speed interfaces and related circuitry.

- `PCIe-M2.kicad_sch`  
  PCIe and M.2 circuitry.

## Libraries

- `CM5IO.pretty/`  
  Custom KiCad footprint library.

- `Image.pretty/`  
  BuggyBot ladybug logo footprints for the silkscreen.

- `CM5IO.3dshapes/`  
  3D models used by PCB footprints.

- `fp-lib-table`  
  KiCad footprint library configuration.

- `sym-lib-table`  
  KiCad symbol library configuration.

## Manufacturing Files (`PCBWay/`)

- `Gerbers/`  
  Gerber files for each copper, mask, paste, silkscreen, and edge-cut layer,
  the plated and non-plated drill files, and the Gerber job file.

- `Gerbers.zip`  
  The same Gerber and drill files in one archive for upload to the board house.

- `Gerbers/IMPEDANCE_CONTROL.txt`  
  Stackup and controlled-impedance requirements for the board house
  (100 Ω and 90 Ω differential pairs, 50 Ω single-ended).

- `BuggyBotBOM.xlsx`  
  Bill of materials for the BuggyBot board.

- `CM5IO-all-pos.csv`  
  Pick-and-place (component position) file for assembly.

## Other Files

- `CM5IOBOM.txt`  
  Bill of Materials from the original CM5 IO Board design.

## Opening the Project

1. Install KiCad 10 or a compatible newer version.
2. Clone or download the BuggyBot repository.
3. Navigate to:

   `Hardware/BuggyBot KiCAD`

4. Open:

   `CM5IO.kicad_pro`

Opening the `.kicad_pro` file should load the schematic, PCB, and associated project libraries.

## Project Purpose

These files are the final design for BuggyBot's custom PCB. The board has not yet been received or tested.

The original CM5 IO Board contains some different hardware than BuggyBot requires. The team is identifying which CM5 support circuitry and interfaces the final board must keep, and adding connectors for BuggyBot's sensors and display. The IMU and LCD ports were added in October 2026. A component checklist and a review of which CM5 features to keep, remove, or modify were also made in October 2026; the checklist itself is not committed to this repository.
