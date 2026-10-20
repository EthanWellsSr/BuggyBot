import copy
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

PROJECT = "Self Driving RC Car"
DATE = "10/20/2026"
SUMMARY_DATE = "10/20/2026"

members = ["Ethan Wells (Group Leader)", "Alexis Perez", "Ethan Bishop", "Abigail Duran"]

summary = (
    "This week the team tested the traffic-sign classifier with BuggyBot's own camera, studied ROS 2 for the vehicle software, "
    "and continued the custom PCB design. "
    "Ethan Wells completed last week's goal of printing the sign cards and photographing them with the Raspberry Pi Camera Module 3 on the CM5. "
    "He captured 10 of the 12 sign classes under three lighting conditions (no light, sunlight, and sunlight plus artificial light) and cut 329 sign crops with an OpenCV template-matching script. "
    "On those 329 camera crops the combined model classified every crop correctly (100% top-1), against 47.7% for the LISA model and 79.9% for the Mapillary model. "
    "The crops were cut with each sign's known class, so this measures sign classification and not automatic sign detection. "
    "He also reorganized the Hardware and Model Training folders, updated the maintained documentation, and repaired the links to the moved files. "
    "Alexis Perez continued his OpenCV learning and tested OpenCV on a webcam, ordered a car chassis so the vehicle components can be tested together, "
    "and wrote a TCRT5000 IR line-sensor script for the Raspberry Pi that reads the left and right course-line sensors on GPIO17 and GPIO27 and reports a lane action. "
    "Ethan Bishop installed ROS 2 under Windows Subsystem for Linux and drafted the node architecture for the vehicle: camera, sign detector, line sensor, IMU, behavior, motor driver, LCD, and teleop. "
    "He also drafted the data flow, in which the behavior node turns lane, sign, and IMU data into driving decisions. "
    "Abigail Duran created an organized component checklist for the PCB design, reviewed the CM5 IO Board components and connections to decide which features are kept, removed, or modified, "
    "and added the IMU and LCD connectors to the board layout. "
    "Connecting the combined classifier to the CM5 camera and LCD pipeline, and measuring crops taken without using the known sign class, carry into next week."
)

plan = [
    ("Ethan Wells", "Connect the combined classifier to the CM5 camera and LCD pipeline, evaluate automatic sign crops that do not use the known sign class, and capture new setups at measured distances and angles while recording accuracy and inference time."),
    ("Alexis Perez", "Implement OpenCV with the Raspberry Pi camera."),
    ("Ethan Bishop", "Create a test program for the ROS 2 implementation."),
    ("Abigail Duran", "Continue developing the PCB design and component placement, and work toward finalizing the PCB design for manufacturing."),
]

contributions = [
    ("Ethan Wells", [("", "Photographed the printed sign cards with the CM5 camera: 10 sign classes under three lighting conditions, cut into 329 sign crops with an OpenCV template-matching script", 5),
                     ("", "Scored the LISA, Mapillary, and combined models on the same 329 camera crops (combined 329 of 329 correct, LISA 47.7%, Mapillary 79.9%)", None),
                     ("", "Reorganized the Hardware and Model Training folders, updated the maintained documentation, and repaired links to the moved files", 1),
                     ("", "Prepared the weekly slides and report", 1)]),
    ("Alexis Perez", [("", "Continued the OpenCV course and tested OpenCV on a webcam", 2),
                      ("", "Ordered a car chassis to test the vehicle components together", 1),
                      ("", "Wrote a TCRT5000 IR line-sensor script for the Raspberry Pi that reads the left and right course-line sensors and reports a lane action", 3)]),
    ("Ethan Bishop", [("", "Installed ROS 2 under Windows Subsystem for Linux and drafted the ROS 2 node structure for the camera, sign detector, line sensor, IMU, behavior, motor driver, LCD, and teleop", 4),
                      ("", "Drafted the ROS 2 data flow in which the behavior node turns lane, sign, and IMU data into driving decisions", 2)]),
    ("Abigail Duran", [("", "Created an organized component checklist/spreadsheet for the PCB design", 2),
                       ("", "Reviewed the CM5 IO Board components and connections to determine which features should be kept, removed, or modified", 2),
                       ("", "Added the IMU and LCD connectors to the board layout", 2)]),
]

hours = [("Ethan Wells", "7", "48"), ("Alexis Perez", "6", "41"),
         ("Ethan Bishop", "6", "40"), ("Abigail Duran", "6", "41")]

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
