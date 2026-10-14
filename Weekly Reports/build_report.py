import copy
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

PROJECT = "Self Driving RC Car"
DATE = "10/13/2026"
SUMMARY_DATE = "10/13/2026"

members = ["Ethan Wells (Group Leader)", "Alexis Perez", "Ethan Bishop", "Abigail Duran"]

summary = (
    "This week the team compared sign-recognition models, outlined a possible software structure for the vehicle, and continued the custom PCB. "
    "Ethan Wells completed last week's goal of training and testing a CNN on the prepared Mapillary sign data. It reached 92.59% accuracy on its 432 test crops. "
    "He then combined the LISA and Mapillary datasets and trained a model on both. On the same 1,016 held-out test crops, the combined model reached 99.31% accuracy, compared with 84.94% for the LISA model and 72.05% for the Mapillary model. "
    "These scores use cropped road-scene images, not BuggyBot's camera, so he prepared printable cards for the 12 sign classes for camera testing. "
    "Alexis Perez completed the OpenCV beginner course and worked on integrating the line sensors with the Raspberry Pi. TCRT5000 IR line sensors and AEDIKO TT motors with wheels were purchased on 10/13. Using OpenCV with the Raspberry Pi camera carries into next week. "
    "Ethan Bishop continued researching ROS 2 and outlined a possible node structure for the vehicle: camera, sign detector, IMU, behavior, motor driver, LCD, and manual-control nodes. "
    "Abigail Duran added the BuggyBot KiCad project files to the repository and removed unnecessary components from the schematic and PCB layout. Component placement, power distribution, and signal routing carry into next week."
)

plan = [
    ("Ethan Wells", "Print the sign cards and capture images of them with the CM5 camera at set distances and angles; score the camera crops separately from the road-scene crop benchmark."),
    ("Alexis Perez", "Implement OpenCV with the Raspberry Pi camera."),
    ("Ethan Bishop", "Continue researching a possible ROS 2 implementation for the vehicle."),
    ("Abigail Duran", "Continue developing the PCB design and component placement, begin planning power distribution and signal routing, and work toward finalizing the PCB design for manufacturing."),
]

contributions = [
    ("Ethan Wells", [("", "Trained and tested the CNN on the Mapillary sign data, reviewed the results, and combined the LISA and Mapillary datasets into 7,601 training, 929 validation, and 1,016 test crops", None),
                     ("", "Trained the combined model (99.31% accuracy on 1,016 test crops) and compared the LISA, Mapillary, and combined models on the same test crops", None),
                     ("", "Prepared printable cards for the 12 sign classes, and prepared the weekly slides and report", None)]),
    ("Alexis Perez", [("", "Completed the OpenCV beginner course", None),
                      ("", "Worked on integrating the line sensors with the Raspberry Pi", None)]),
    ("Ethan Bishop", [("", "Continued researching a possible ROS 2 implementation for the vehicle", None),
                      ("", "Outlined a preliminary ROS 2 node structure for the camera, sign detector, IMU, behavior, motor driver, LCD, and manual control", None)]),
    ("Abigail Duran", [("", "Added the BuggyBot KiCad project files to the repository", None),
                       ("", "Created a component checklist for the PCB design", None),
                       ("", "Removed unnecessary components from the schematic and PCB layout", None)]),
]

hours = [("Ethan Wells", "8", "41"), ("Alexis Perez", "6", "35"),
         ("Ethan Bishop", "6", "34"), ("Abigail Duran", "6", "35")]

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
