import copy
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

PROJECT = "Self Driving RC Car"
DATE = "11/3/2026"
SUMMARY_DATE = "11/3/2026"

members = ["Ethan Wells (Group Leader)", "Alexis Perez", "Ethan Bishop", "Abigail Duran"]

summary = (
    "This week the team tested every BuggyBot component together on the bench, finished the custom PCB design, "
    "and started the project poster and a ROS 2 version of the sign pipeline. "
    "Ethan Wells met both of last week's goals. The integration test passed all seven stages on the Raspberry Pi Compute Module 5 (CM5) I/O board, "
    "powered from the Pi with no motor load: the I2C scan found the LCD and IMU, both TCRT5000 line sensors responded, "
    "and the sign pipeline read a printed card at 98% confidence with 1.9 ms inference at 36 fps. "
    "The test found and fixed two bugs: the line sensor script was missing a required setting, and the I2C scan missed the LCD because the LCD only answers writes. "
    "He read the Cokoino 4WD motor HAT's schematic, found that it needs a 7-12 V input, and bought a 60 W adjustable bench supply. "
    "He then split the test into a per-component test and a stress test that runs the motors, camera and sign model, IMU, line sensors, and LCD all at once. "
    "On 9 V from the bench supply, the 120-second stress test passed with no errors and no under-voltage, and the camera held 30.0 fps against a 30.2 fps baseline. "
    "He also designed a 3D-printed bracket that holds the Camera Module 3 above the I/O board, and gave Abigail Duran final approval to send the PCB design for manufacturing. "
    "Alexis Perez worked on the Semester 1 project poster (due 11/5) instead of last week's goal of fine-tuning OpenCV: he collected the project information and results and designed the poster. "
    "Ethan Bishop partly met his goal of a first ROS 2 node on the CM5: he wrote a preliminary ROS 2 version of the sign pipeline with camera, sign classifier, and LCD nodes. "
    "It runs in Docker on a development machine, because ROS 2 has no Raspberry Pi OS packages, and has not yet run on the CM5 or been added to the repository. "
    "He also reprinted the camera bracket taller (170 mm), wider, and with a larger brace, helped with the stress test, and supplied a battery to make the test setup mobile. "
    "Abigail Duran finished tracing the connections on the PCB and generated the manufacturing files: Gerbers, bill of materials, and pick-and-place."
)

plan = [
    ("Ethan Wells", "Write the Self-analysis, Project, and Technical Reports (due 11/19) and fine-tune OpenCV detection in the Pi sign demo."),
    ("Alexis Perez", "Plan how the vision model will be integrated with the vehicle."),
    ("Ethan Bishop", "Run the ROS 2 sign program on the CM5 with the camera on the new mount."),
    ("Abigail Duran", "Receive the PCB and begin testing it."),
]

# Per-task hours are omitted; the Hour Tracker carries each member's weekly
# total from their slide.
contributions = [
    ("Ethan Wells", [("", "Ran the integration test on the CM5 I/O board: all seven stages passed; fixed the line sensor and LCD detection bugs it found", None),
                     ("", "Read the Cokoino HAT schematic and bought a 60 W adjustable bench supply for its 7-12 V input", None),
                     ("", "Split the test into test_components.py and stress_test.py; the 120-second stress test passed on 9 V with no errors or under-voltage at 30.0 fps", None),
                     ("", "Designed a 3D-printed Camera Module 3 bracket for the CM5 I/O board", None),
                     ("", "Gave Abigail Duran final approval to send the PCB design for manufacturing", None),
                     ("", "Prepared the weekly slides and report", None)]),
    ("Alexis Perez", [("", "Collected project information and results for the Semester 1 poster", None),
                      ("", "Designed the project poster", None)]),
    ("Ethan Bishop", [("", "Wrote a preliminary ROS 2 version of the sign pipeline (camera, sign classifier, and LCD nodes), running in Docker", None),
                      ("", "Reprinted the camera bracket taller (170 mm), wider, and with a larger brace", None),
                      ("", "Helped with the stress test and supplied a battery to make the test setup mobile", None)]),
    ("Abigail Duran", [("", "Finished tracing the connections on the PCB", None),
                       ("", "Generated the manufacturing files: Gerbers, bill of materials, and pick-and-place", None)]),
]

hours = [("Ethan Wells", "6", "64"), ("Alexis Perez", "6", "54"),
         ("Ethan Bishop", "7", "53"), ("Abigail Duran", "6", "53")]

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
