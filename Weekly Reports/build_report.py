import copy
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

PROJECT = "Self Driving RC Car"
DATE = "9/22/2026"
SUMMARY_DATE = "9/22/2026"

members = ["Ethan Wells (Group Leader)", "Alexis Perez", "Ethan Bishop", "Abigail Duran"]

summary = ("This week the team moved from selecting parts to testing them on hardware. "
    "Ethan Wells set the machine-learning goals aside to get the compute ready for the rest of the team: he assembled the Raspberry Pi Compute Module 5 on the Compute Module 5 IO Board with its heatsink and PWM fan, CR2032 real-time-clock battery, and 27 W USB-C power supply, "
    "flashed Raspberry Pi OS Lite (64-bit) to the 128 GB NVMe solid-state drive that the board boots from, and brought the board up headless over SSH through a USB Wi-Fi dongle, which the CM5 needs because it has no onboard wireless; "
    "he traced very slow SSH throughput to the dongle's stock driver and replaced it with a working one, and wrote setup.sh so any team member can install the shared software prerequisites on a board with one command. "
    "Alexis Perez finalized the ultrasonic sensor implementation on the Pi, which measures distance to obstacles and walls, and tested the TT-style drive motors and L298N motor controller, finding performance issues that may require replacement parts; he also determined the hardware power requirements that will drive battery selection. "
    "Ethan Bishop ordered 2WD and 4WD Raspberry Pi HAT motor controllers and wrote code to test them for operational accuracy, and continued implementing the IMU, the sensor that reports the vehicle's heading and turns, verifying its measurements and directions. "
    "Abigail Duran prepared the libraries and software for the LCD1602 RGB status display, researched camera setup and configuration for the CM5, and identified the steps needed to integrate the camera and display with the machine-learning model.")

plan = [
    ("Ethan Wells", "Prepare the LISA dataset (US traffic signs) for training and test the trained German-sign (GTSRB) model."),
    ("Alexis Perez", "Select replacement motors and motor controller if the tested parts do not meet requirements, and narrow down the battery and power-supply options."),
    ("Ethan Bishop", "Finish testing the Pi HAT motor controllers, finish the IMU implementation on the Raspberry Pi, and research 3D-printable STL files for the chassis."),
    ("Abigail Duran", "Continue hardware testing and verify communication between the Raspberry Pi and all connected components, determine which components and connections go on the final PCB, and begin the PCB layout including component placement, board dimensions, power distribution, and signal routing."),
]

contributions = [
    ("Ethan Wells", [("9/19/2026", "Assembled the CM5 on the Compute Module 5 IO Board with the heatsink and PWM fan, CR2032 RTC battery, and 27 W USB-C power supply, then flashed Raspberry Pi OS Lite (64-bit) to the 128 GB NVMe SSD and booted the board from M.2", 3),
                     ("9/21/2026", "Brought up headless SSH over the USB Wi-Fi dongle and, after tracing very slow SSH throughput to the dongle's stock driver, replaced it with a working driver", 2),
                     ("9/23/2026", "Wrote setup.sh, a one-command install of the shared software prerequisites (git, python3, pip, venv), and updated the parts list with the remaining compute purchases", 2)]),
    ("Alexis Perez", [("", "Finalized the ultrasonic sensor implementation on the Raspberry Pi, including additional distance-reading and range testing", None),
                      ("", "Tested the TT-style drive motors and L298N motor controller for performance and identified issues with the current components", None),
                      ("", "Determined the hardware power requirements to guide battery and power-supply selection", None)]),
    ("Ethan Bishop", [("", "Ordered 2WD and 4WD Raspberry Pi HAT motor controllers and wrote code to test them for operational accuracy", None),
                      ("", "Continued implementing the IMU on the Raspberry Pi and verified its measurements and directions", None)]),
    ("Abigail Duran", [("", "Prepared the necessary libraries and software for the LCD1602 RGB display module", None),
                       ("", "Researched camera setup and configuration for the Raspberry Pi Compute Module 5", None),
                       ("", "Identified the steps needed to integrate the camera and LCD with the machine-learning model", None)]),
]

hours = [("Ethan Wells", "7", "19"), ("Alexis Perez", "7", "16"),
         ("Ethan Bishop", "6", "15"), ("Abigail Duran", "6", "17")]

d = Document("project_name.docx")

def para_by(pred):
    for p in d.paragraphs:
        if pred(p.text):
            return p
    raise SystemExit("anchor not found: " + repr(pred))

def add_run(p_el, text, bold=False, underline=False):
    r = OxmlElement('w:r'); rpr = OxmlElement('w:rPr')
    if bold:
        rpr.append(OxmlElement('w:b'))
    if underline:
        u = OxmlElement('w:u'); u.set(qn('w:val'), 'single'); rpr.append(u)
    sz = OxmlElement('w:sz'); sz.set(qn('w:val'), '24'); rpr.append(sz)   # 12pt
    r.append(rpr)
    t = OxmlElement('w:t'); t.set(qn('xml:space'), 'preserve'); t.text = text; r.append(t)
    p_el.append(r)
    return r

# normal-body paragraph template (clone the summary instruction paragraph, keep its pPr)
p_sum_head = para_by(lambda t: t.startswith("Weekly Summary"))
sum_instr = p_sum_head._p.getnext()          # the instruction paragraph after the heading
normal_tmpl = copy.deepcopy(sum_instr)

def new_normal():
    el = copy.deepcopy(normal_tmpl)
    for r in el.findall(qn('w:r')): el.remove(r)
    return el

def line_para(runs):
    """runs = list of (text, bold, underline)"""
    el = new_normal()
    for text, b, u in runs:
        add_run(el, text, b, u)
    return el

# 1) Project Title
p_title = para_by(lambda t: t.startswith("Project Title"))
rs = p_title.runs
rs[0].text = "Project Title: "
rs[1].text = PROJECT
for r in rs[2:]: r.text = ""

# 2) Date
p_date = para_by(lambda t: t.startswith("Date:"))
rs = p_date.runs
rs[0].text = "Date: "
rs[1].text = DATE
for r in rs[2:]: r.text = ""

# 3) Project Members -> insert one line per member after the heading
p_mem = para_by(lambda t: t.strip() == "Project Members:")
anchor = p_mem._p
# remove the single blank paragraph the template puts right after members, if present
nxt = anchor.getnext()
if nxt is not None and nxt.tag == qn('w:p') and not nxt.findall(qn('w:r')):
    nxt.getparent().remove(nxt)
for m in members:
    el = line_para([(m, False, False)])
    anchor.addnext(el); anchor = el

# 4) Weekly Summary heading date + body
sum_runs = p_sum_head.runs   # capture once: p_sum_head.runs[0] would be a fresh object each call
for i, r in enumerate(sum_runs):
    r.text = "Weekly Summary (%s):" % SUMMARY_DATE if i == 0 else ""
# replace instruction paragraph content with the summary
for r in list(sum_instr.findall(qn('w:r'))): sum_instr.remove(r)
add_run(sum_instr, summary, False, False)

# 5) Proposed Plan -> per-member lines replacing the instruction paragraph
p_plan_head = para_by(lambda t: t.startswith("Proposed Plan"))
plan_instr = p_plan_head._p.getnext()
# turn the instruction paragraph into the first member's line
for r in list(plan_instr.findall(qn('w:r'))): plan_instr.remove(r)
n0, g0 = plan[0]
add_run(plan_instr, n0 + ": ", False, True)
add_run(plan_instr, g0, False, False)
anchor = plan_instr
for n, g in plan[1:]:
    el = line_para([(n + ": ", False, True), (g, False, False)])
    anchor.addnext(el); anchor = el

# 6) Weekly Contributions -> remove everything between the heading and Hour Tracker, rebuild
p_contrib = para_by(lambda t: t.strip() == "Weekly Contributions:")
p_hour = para_by(lambda t: t.strip() == "Hour Tracker:")
start = p_contrib._p
stop = p_hour._p
# collect elements strictly between start and stop
to_remove = []
cur = start.getnext()
while cur is not None and cur is not stop:
    to_remove.append(cur)
    cur = cur.getnext()
for el in to_remove:
    el.getparent().remove(el)
# rebuild contributions after the heading
anchor = start
for name, entries in contributions:
    head = line_para([(name + ":", False, True)])
    anchor.addnext(head); anchor = head
    for date, text, hrs in entries:
        line = ("%s – %s" % (date, text)) if date else text   # date optional
        if hrs is not None:                                   # hours optional (placeholder)
            unit = "hour" if hrs == 1 else "hours"
            line += " (%d %s)" % (hrs, unit)
        el = line_para([(line, False, False)])
        anchor.addnext(el); anchor = el
# one blank spacer before Hour Tracker
spacer = new_normal()
anchor.addnext(spacer)

# 7) Hour Tracker table
tbl = d.tables[0]
def set_cell(cell, text):
    p = cell.paragraphs[0]
    for r in list(p._p.findall(qn('w:r'))): p._p.remove(r)
    add_run(p._p, text, False, False)
for i, (name, wk, cum) in enumerate(hours):
    row = tbl.rows[i + 1]
    set_cell(row.cells[0], name)
    set_cell(row.cells[1], wk)
    set_cell(row.cells[2], cum)

d.save("Self_Driving_RC_Car.docx")
print("saved")
