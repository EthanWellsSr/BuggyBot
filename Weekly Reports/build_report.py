import copy
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

PROJECT = "Self Driving RC Car"
DATE = "10/27/2026"
SUMMARY_DATE = "10/27/2026"

members = ["Ethan Wells (Group Leader)", "Alexis Perez", "Ethan Bishop", "Abigail Duran"]

summary = (
    "This week the team ran live traffic-sign recognition on BuggyBot, built a test script for every sensor and the motor driver, "
    "and continued the custom PCB design. "
    "Alexis Perez met last week's goal of implementing OpenCV with the Raspberry Pi camera: he wrote the first sign-detection demo script for the CM5, "
    "which captures frames from the Raspberry Pi Camera Module 3, finds sign-shaped regions with OpenCV, classifies them with the combined model, and shows the result on the LCD. "
    "He also moved the TCRT5000 line sensors to GPIO20 and GPIO21 so they no longer share pins with the Cokoino motor HAT. "
    "Ethan Wells met two of last week's three goals. He connected the combined classifier to the CM5 camera and LCD through Alexis's demo and tested it live with signs located automatically, without using the known sign class. "
    "Live testing showed false detections, so he added a browser video stream (the Pi has no desktop), LCD backlight colors by sign, color and shape checks that stop hands, faces, and shirts from being read as stop signs, "
    "whole-sign cropping so the added-lane sign is no longer read as merge, and a rule that the same sign must be read on 3 frames in a row before it reaches the LCD. "
    "In the final live test all 10 printed sign classes were shown 3 times each over two runs, and 60 of 60 LCD outputs were correct. "
    "He documented the problems and fixes in a troubleshooting guide. Measuring accuracy and inference time at set distances and angles carries into a later week. "
    "Ethan Bishop built a master test script that checks the line sensors, IMU, camera, LCD, and motor driver in turn and prints a pass/fail summary, "
    "ran the ROS 2 turtlesim tutorial under Windows Subsystem for Linux, and started the ROS 2 test program from last week's goal. "
    "Abigail Duran continued the PCB design toward manufacturing: she added the required new components to the board, began tracing the connections, "
    "and ordered STEMMA QT / Qwiic I2C cables for connecting the I2C boards."
)

plan = [
    ("Ethan Wells", "Run a full sensor test on the CM5 I/O board, then give Abigail Duran final approval to send the PCB design for manufacturing."),
    ("Alexis Perez", "Fine-tune OpenCV on the Raspberry Pi and test all components."),
    ("Ethan Bishop", "Write a first ROS 2 test node and run it on the CM5."),
    ("Abigail Duran", "Generate all required files for manufacturing and place the PCB order."),
]

# Per-task hours are omitted this week; the Hour Tracker carries each member's
# weekly total from their slide.
contributions = [
    ("Ethan Wells", [("", "Connected the combined classifier to the CM5 camera and LCD through Alexis Perez's sign demo and tested it live on BuggyBot", None),
                     ("", "Fixed false detections found in live testing: color and shape checks, whole-sign cropping, and 3-frame confirmation; added a browser video stream and LCD colors by sign", None),
                     ("", "Final live test: 60 of 60 LCD outputs correct (10 sign classes, 3 times each over two runs)", None),
                     ("", "Wrote the OpenCV troubleshooting guide documenting each problem and fix", None),
                     ("", "Prepared the weekly slides and report", None)]),
    ("Alexis Perez", [("", "Wrote the first sign-detection demo script for the CM5: Pi camera, OpenCV sign regions, combined model, and LCD output", None),
                      ("", "Tested OpenCV with a laptop webcam and wrote OpenCV setup instructions and test scripts", None),
                      ("", "Moved the line sensors to GPIO20 and GPIO21 to avoid a pin clash with the Cokoino motor HAT", None)]),
    ("Ethan Bishop", [("", "Built a master test script for every sensor and the motor driver (line sensors, IMU, camera, LCD, motors) with a pass/fail summary", None),
                      ("", "Ran the ROS 2 turtlesim tutorial under Windows Subsystem for Linux", None),
                      ("", "Started the ROS 2 test program", None)]),
    ("Abigail Duran", [("", "Added the required new components to the PCB design", None),
                       ("", "Began tracing the connections on the board", None),
                       ("", "Ordered STEMMA QT / Qwiic I2C cables", None)]),
]

hours = [("Ethan Wells", "10", "58"), ("Alexis Perez", "7", "48"),
         ("Ethan Bishop", "6", "46"), ("Abigail Duran", "6", "47")]

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

# Use each paragraph type from the TA's template: plain project members,
# first-level bullets for plans and contribution names, and nested bullets for tasks.
p_mem = para_by(lambda t: t.strip() == "Project Members:")
p_sum_head = para_by(lambda t: t.startswith("Weekly Summary"))
p_plan_head = para_by(lambda t: t.startswith("Proposed Plan"))
p_contrib = para_by(lambda t: t.strip() == "Weekly Contributions:")
p_hour = para_by(lambda t: t.strip() == "Hour Tracker:")
member_slot = p_mem._p.getnext()
sum_instr = p_sum_head._p.getnext()
plan_instr = p_plan_head._p.getnext()
member_tmpl = copy.deepcopy(member_slot)
plan_tmpl = copy.deepcopy(plan_instr)
contrib_head_tmpl = copy.deepcopy(p_contrib._p.getnext())
contrib_task_tmpl = copy.deepcopy(p_contrib._p.getnext().getnext())

def fill_para(el, runs):
    """Replace text while preserving the template paragraph's list level and spacing."""
    for r in list(el.findall(qn('w:r'))):
        el.remove(r)
    for text, bold, underline in runs:
        add_run(el, text, bold, underline)
    return el

def clone_para(template, runs):
    return fill_para(copy.deepcopy(template), runs)

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

# 3) Project Members -> fill the plain paragraph, then repeat it
fill_para(member_slot, [(members[0], False, False)])
anchor = member_slot
for m in members[1:]:
    el = clone_para(member_tmpl, [(m, False, False)])
    anchor.addnext(el); anchor = el

# 4) Weekly Summary heading date + body
sum_runs = p_sum_head.runs   # capture once: p_sum_head.runs[0] would be a fresh object each call
for i, r in enumerate(sum_runs):
    r.text = "Weekly Summary (%s):" % SUMMARY_DATE if i == 0 else ""
# replace the template's first-level summary bullet
fill_para(sum_instr, [(summary, False, False)])

# 5) Proposed Plan -> repeat the template's first-level plan bullet
n0, g0 = plan[0]
fill_para(plan_instr, [(n0 + ": ", False, True), (g0, False, False)])
anchor = plan_instr
for n, g in plan[1:]:
    el = clone_para(plan_tmpl, [(n + ": ", False, True), (g, False, False)])
    anchor.addnext(el); anchor = el

# 6) Weekly Contributions -> repeat the template's name/task list levels
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
anchor = start
for name, entries in contributions:
    head = clone_para(contrib_head_tmpl, [(name + ":", False, True)])
    anchor.addnext(head); anchor = head
    for date, text, hrs in entries:
        line = ("%s – %s" % (date, text)) if date else text   # date optional
        if hrs is not None:                                   # hours optional (placeholder)
            unit = "hour" if hrs == 1 else "hours"
            line += " (%d %s)" % (hrs, unit)
        el = clone_para(contrib_task_tmpl, [(line, False, False)])
        anchor.addnext(el); anchor = el
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
