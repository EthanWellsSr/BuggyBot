import copy
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

PROJECT = "Self Driving RC Car"
DATE = "9/29/2026"
SUMMARY_DATE = "9/29/2026"

members = ["Ethan Wells (Group Leader)", "Alexis Perez", "Ethan Bishop", "Abigail Duran"]

summary = ("This week the team finished bench-testing the core hardware on the Raspberry Pi and moved the sign-recognition model onto US traffic signs. "
    "Ethan Wells completed both of last week's machine-learning goals: he prepared the LISA Traffic Signs dataset (US signs) for training, writing prepare_lisa.py to validate the download, crop each annotated sign, and split the crops into training, validation, and test sets, "
    "narrowing the dataset's 47 sign classes to the 12 the car needs (6,097 cropped signs) and keeping every frame of the same physical sign in one split so near-identical images cannot appear in both training and testing; "
    "he also tested the German-sign (GTSRB) model on the 12,630-image GTSRB test set, where it reached 95.8% accuracy. "
    "Alexis Perez researched and presented the vehicle navigation options the team can use to follow the course, and completed an OpenCV course in preparation for the camera and image-processing pipeline. "
    "Ethan Bishop finished testing the Raspberry Pi HAT motor controllers for operational accuracy, running both HATs over I2C on the 40-pin GPIO header, and finished implementing the IMU, the sensor that reports the vehicle's heading and turns, over I2C and verified its measurements and directions; research on 3D-printable chassis files carries over to next week. "
    "Abigail Duran connected and communicated with the LCD status display and the camera from the Raspberry Pi Compute Module 5, and integrated both with the machine-learning model so detected signs and their corresponding commands are shown on the display.")

plan = [
    ("Ethan Wells", "Train a CNN on the prepared 12-class LISA dataset (US traffic signs) and test it on the LISA test split."),
    ("Alexis Perez", "Research and purchase any components still missing for the selected navigation option, and continue learning OpenCV for the camera pipeline."),
    ("Ethan Bishop", "Research 3D-printable STL files for the chassis and research a possible ROS implementation for the vehicle."),
    ("Abigail Duran", "Begin planning the PCB layout, including component placement and board dimensions, and begin planning power distribution and signal routing."),
]

contributions = [
    ("Ethan Wells", [("9/26/2026", "Downloaded the LISA Traffic Signs dataset from the Kaggle mirror after the UCSD download host was unavailable, and began the dataset preparation script", 2),
                     ("9/28/2026", "Finished prepare_lisa.py, which validates the dataset, crops each annotated sign, narrows the 47 classes to the 12 the car needs, and splits the 6,097 crops by sign track into training, validation, and test sets; documented the steps in LISA_PREPARATION.md", 2),
                     ("9/29/2026", "Tested the German-sign (GTSRB) model on the 12,630-image GTSRB test set, reaching 95.8% accuracy, and saved the results to gtsrb_test_results.json", 3)]),
    ("Alexis Perez", [("", "Researched, finalized, and presented the vehicle navigation options", None),
                      ("", "Completed an OpenCV course in preparation for the camera and image-processing pipeline", None)]),
    ("Ethan Bishop", [("", "Tested the Raspberry Pi HAT motor controllers for operational accuracy, running both HATs over I2C on the 40-pin GPIO header", None),
                      ("", "Implemented the IMU on the Raspberry Pi over I2C and verified its measurements and directions", None)]),
    ("Abigail Duran", [("", "Connected and communicated with the LCD and camera using the Raspberry Pi Compute Module 5", None),
                       ("", "Integrated the LCD and camera with the machine-learning model to display detected signs and their corresponding commands", None)]),
]

hours = [("Ethan Wells", "7", "26"), ("Alexis Perez", "7", "23"),
         ("Ethan Bishop", "7", "22"), ("Abigail Duran", "6", "23")]

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
