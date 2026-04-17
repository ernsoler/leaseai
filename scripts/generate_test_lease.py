"""
Generate a realistic test lease agreement PDF modelled on the official
Florida Residential Lease for Single Family Home or Duplex form.

All blanks are filled with synthetic but realistic data. Several clauses
are intentionally landlord-favourable to give the AI analysis model
meaningful risk signals to flag.

Usage:
    python scripts/generate_test_lease.py
Output:
    lease_agreement_test.pdf (in project root)
"""
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

OUTPUT = os.path.join(os.path.dirname(__file__), "..", "lease_agreement_test.pdf")

# ── Styles ────────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    "title", parent=styles["Title"], fontSize=14,
    spaceAfter=2, alignment=TA_CENTER, fontName="Helvetica-Bold",
)
subtitle_style = ParagraphStyle(
    "subtitle", parent=styles["Normal"], fontSize=9,
    spaceAfter=2, alignment=TA_CENTER, textColor=colors.HexColor("#444444"),
)
warning_style = ParagraphStyle(
    "warning", parent=styles["Normal"], fontSize=8,
    spaceAfter=4, alignment=TA_CENTER,
    textColor=colors.HexColor("#7b0000"), fontName="Helvetica-Bold",
)
section_style = ParagraphStyle(
    "section", parent=styles["Normal"], fontSize=9,
    spaceBefore=10, spaceAfter=3,
    fontName="Helvetica-Bold",
)
body_style = ParagraphStyle(
    "body", parent=styles["Normal"], fontSize=9,
    leading=13, spaceAfter=4, alignment=TA_JUSTIFY,
)
small_style = ParagraphStyle(
    "small", parent=styles["Normal"], fontSize=8,
    leading=11, spaceAfter=3, alignment=TA_JUSTIFY,
    textColor=colors.HexColor("#333333"),
)
footer_style = ParagraphStyle(
    "footer", parent=styles["Normal"], fontSize=7,
    textColor=colors.grey, alignment=TA_CENTER,
)


def hr(thickness=0.5):
    return HRFlowable(width="100%", thickness=thickness,
                      color=colors.HexColor("#cccccc"), spaceAfter=4)


def sec(num, title):
    return Paragraph(f"{num}.  {title.upper()}.", section_style)


def body(text):
    return Paragraph(text, body_style)


def small(text):
    return Paragraph(text, small_style)


def sp(h=6):
    return Spacer(1, h)


def field(label, value, label_w=1.6 * inch, value_w=5.0 * inch):
    t = Table(
        [[Paragraph(label, small_style), Paragraph(f"<b>{value}</b>", small_style)]],
        colWidths=[label_w, value_w],
    )
    t.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def box_table(rows, col_widths=None):
    """Generic bordered table."""
    cw = col_widths or [2.5 * inch, 4.1 * inch]
    t = Table(rows, colWidths=cw)
    t.setStyle(TableStyle([
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("BOX",           (0, 0), (-1, -1), 0.5, colors.HexColor("#bbbbbb")),
        ("INNERGRID",     (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
        ("ROWBACKGROUNDS",(0, 0), (-1, -1), [colors.white, colors.HexColor("#f7f8fa")]),
    ]))
    return t


def header_table(rows, header_label):
    """Dark-header table for financial sections."""
    data = [[Paragraph(h, ParagraphStyle("th", parent=styles["Normal"],
                                          fontSize=9, fontName="Helvetica-Bold",
                                          textColor=colors.white))
             for h in header_label]] + rows
    t = Table(data, colWidths=[4.0 * inch, 2.6 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor("#1a3a5c")),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("ALIGN",         (1, 0), (1, -1),  "RIGHT"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f8fa")]),
        ("BOX",           (0, 0), (-1, -1), 0.5, colors.HexColor("#bbbbbb")),
        ("INNERGRID",     (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
    ]))
    return t


def checklist_table(items):
    """Two-column responsibility checklist (Section 10)."""
    rows = []
    for i in range(0, len(items), 2):
        left = items[i]
        right = items[i + 1] if i + 1 < len(items) else ("", "")
        rows.append([
            Paragraph(left[0], small_style),
            Paragraph(f"<b>{left[1]}</b>", small_style),
            Paragraph(right[0], small_style),
            Paragraph(f"<b>{right[1]}</b>", small_style),
        ])
    t = Table(rows, colWidths=[2.1 * inch, 0.8 * inch, 2.1 * inch, 0.8 * inch])
    t.setStyle(TableStyle([
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("BOX",           (0, 0), (-1, -1), 0.5, colors.HexColor("#bbbbbb")),
        ("INNERGRID",     (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
        ("ROWBACKGROUNDS",(0, 0), (-1, -1), [colors.white, colors.HexColor("#f7f8fa")]),
        ("TEXTCOLOR",     (1, 0), (1, -1),  colors.HexColor("#7b0000")),
        ("TEXTCOLOR",     (3, 0), (3, -1),  colors.HexColor("#7b0000")),
    ]))
    return t


# ── Build document ─────────────────────────────────────────────────────────────
doc = SimpleDocTemplate(
    OUTPUT,
    pagesize=letter,
    leftMargin=0.85 * inch, rightMargin=0.85 * inch,
    topMargin=0.75 * inch,  bottomMargin=0.75 * inch,
)

story = []

# ── Cover / Title ─────────────────────────────────────────────────────────────
story += [
    Paragraph("RESIDENTIAL LEASE FOR SINGLE FAMILY HOME", title_style),
    Paragraph("State of Florida — Single Family Home / Duplex", subtitle_style),
    Paragraph(
        "THIS LEASE IMPOSES IMPORTANT LEGAL OBLIGATIONS. MANY RIGHTS AND RESPONSIBILITIES "
        "OF THE PARTIES ARE GOVERNED BY CHAPTER 83, PART II, FLORIDA RESIDENTIAL LANDLORD "
        "AND TENANT ACT.",
        warning_style,
    ),
    sp(4), hr(1), sp(4),
]

# ── Section 1: Parties ────────────────────────────────────────────────────────
story.append(sec("1", "Parties"))
story += [
    body(
        'This is a lease ("the Lease") between <b>Sunrise Realty Group LLC</b>, '
        '8500 NW 36th Street, Suite 200, Doral, FL 33166 ("Landlord") and '
        "<b>Jordan Miller &amp; Taylor Brooks</b>, currently residing at "
        '1420 SW 27th Ave, Apt 4D, Miami, FL 33145 ("Tenant").'
    ),
    field("Landlord e-mail:", "leasing@sunriserealty.com"),
    field("Landlord phone:", "(305) 888-4400"),
    field("Tenant e-mail:", "jmiller@email.com"),
    field("Tenant phone:", "(786) 555-0772"),
    sp(6),
]

# ── Section 2: Property ───────────────────────────────────────────────────────
story.append(sec("2", "Property Rented"))
story += [
    body(
        "Landlord leases to Tenant the land and buildings located at "
        "<b>3847 Coral Ridge Drive, Coral Springs, FL 33065</b> "
        "together with the following furniture and appliances:"
    ),
    box_table([
        ["Property Type:",     "Single-Family Home"],
        ["Bedrooms / Baths:",  "3 Bedrooms / 2 Bathrooms"],
        ["Square Footage:",    "1,820 sq ft"],
        ["Garage:",            "2-car attached garage"],
        ["Appliances included:", "Refrigerator, Range/Oven, Dishwasher, Washer, Dryer"],
        ["Furnished:",         "Unfurnished"],
        ["Pool:",              "Yes — screened in-ground pool (see Section 10)"],
    ], col_widths=[2.0 * inch, 4.6 * inch]),
    sp(4),
    body("Occupants: Jordan Miller, Taylor Brooks, and minor child (age 4) only."),
    sp(6),
]

# ── Section 3: Term ───────────────────────────────────────────────────────────
story.append(sec("3", "Term"))
story += [
    box_table([
        ["Lease Start Date:", "June 1, 2026"],
        ["Lease End Date:",   "May 31, 2027"],
        ["Lease Type:",       "Fixed-term (12 months). NOT TO EXCEED ONE YEAR."],
    ], col_widths=[2.0 * inch, 4.6 * inch]),
    sp(6),
]

# ── Section 4: Rent ───────────────────────────────────────────────────────────
story.append(sec("4", "Rent Payments, Taxes and Charges"))
story += [
    body(
        "Tenant shall pay total rent in the amount of <b>$38,400.00</b> (excluding taxes) "
        "for the Lease Term, payable in monthly installments of <b>$3,200.00</b> per month, "
        "due on the <b>1st day</b> of each month. All rent payments shall be payable to "
        "Sunrise Realty Group LLC at the address above."
    ),
    body(
        "<b>Payment Methods:</b> Personal check, money order, cashier's check, or ACH bank transfer. "
        "Cash will NOT be accepted. If Tenant makes a rent payment with a worthless check, Landlord "
        "may require all future payments by cashier's check or money order only, and Tenant shall "
        "pay a bad-check fee of <b>$150.00</b> per occurrence."
    ),
    body(
        "<b>Proration:</b> If tenancy commences on a day other than the 1st, rent shall be prorated "
        "at $106.67/day based on a 30-day month."
    ),
    sp(6),
]

# ── Section 5: Money Due at Occupancy ─────────────────────────────────────────
story.append(sec("5", "Money Due Prior to Occupancy"))
story += [
    body("Tenant shall pay the following amounts prior to receiving keys and occupying the Premises:"),
    sp(3),
    header_table(
        rows=[
            [small("First month's rent (June 2026)"),          small("<b>$3,200.00</b>")],
            [small("Last month's rent (May 2027)"),             small("<b>$3,200.00</b>")],
            [small("Security deposit (2 months' rent)"),        small("<b>$6,400.00</b>")],
            [small("Non-refundable administrative fee"),        small("<b>$500.00</b>")],
            [small("Pet deposit (non-refundable — 1 dog)"),    small("<b>$400.00</b>")],
            [small("HOA application fee (paid by Tenant)"),    small("<b>$175.00</b>")],
            [small("<b>TOTAL DUE AT SIGNING</b>"),             small("<b>$13,875.00</b>")],
        ],
        header_label=["Item", "Amount"],
    ),
    sp(4),
    small(
        "Tenant shall not be entitled to move in or receive keys until all amounts above are paid "
        "in full via cashier's check or wire transfer. Personal checks will not be accepted for "
        "move-in funds."
    ),
    sp(6),
]

# ── Section 6: Late Fees ──────────────────────────────────────────────────────
story.append(sec("6", "Late Fees"))
story += [
    body(
        "In addition to rent, Tenant shall pay a late charge of <b>$200.00</b> for each monthly "
        "rent payment received after the <b>3rd day</b> of the month, plus an additional "
        "<b>$75.00 per day</b> for each day rent remains unpaid beyond the 3-day grace period. "
        "Landlord may apply any partial payment first to outstanding fees and penalties before "
        "crediting rent, regardless of Tenant's written designation."
    ),
    sp(6),
]

# ── Section 7: Pets & Smoking ─────────────────────────────────────────────────
story.append(sec("7", "Pets and Smoking"))
story += [
    body(
        "One (1) domestic dog not exceeding <b>35 lbs</b> at full adult weight is permitted "
        "upon payment of the non-refundable pet deposit. The following breeds are prohibited at "
        "Landlord's sole discretion: Pit Bull, Rottweiler, Doberman Pinscher, German Shepherd, "
        "Chow Chow, Siberian Husky, Alaskan Malamute, and any mix thereof. Landlord may revoke "
        "pet permission at any time upon <b>14 days</b> written notice. Tenant is liable for all "
        "pet-related damage, including landscaping damage."
    ),
    body(
        "<b>Smoking:</b> Smoking of any substance — including tobacco, cannabis, e-cigarettes, "
        "and vaping devices — is strictly prohibited inside the Premises and within 25 feet of any "
        "door or window. Violation results in a $500 fine per occurrence and grounds for eviction."
    ),
    sp(6),
]

# ── Section 8: Notices ────────────────────────────────────────────────────────
story.append(sec("8", "Notices"))
story += [
    body(
        "Landlord's Agent: <b>Marco Reyes, Licensed Real Estate Broker</b>. "
        "All notices must be sent to Landlord at: Sunrise Realty Group LLC, "
        "8500 NW 36th Street, Suite 200, Doral, FL 33166. "
        "All notices shall be delivered by <b>U.S. Certified Mail or hand delivery only</b>. "
        "Email or text message shall NOT constitute valid legal notice under this Lease."
    ),
    sp(6),
]

# ── Section 9: Utilities ──────────────────────────────────────────────────────
story.append(sec("9", "Utilities"))
story += [
    body(
        "Tenant shall pay for ALL utility services during the Lease Term, including connection "
        "charges and deposits, EXCEPT: <b>HOA fees</b>, which Landlord agrees to pay at Landlord's "
        "expense."
    ),
    box_table([
        ["Electricity:",          "Tenant — FPL account"],
        ["Water &amp; Sewer:",    "Tenant — City of Coral Springs (no cap)"],
        ["Natural Gas:",          "Tenant"],
        ["Internet / Cable:",     "Tenant"],
        ["Trash Collection:",     "Tenant — City service (billed through water account)"],
        ["Lawn / Irrigation:",    "Tenant — responsible for water used for irrigation"],
        ["Pool Chemicals:",       "Tenant — see Section 10"],
        ["HOA Fees:",             "Landlord (Coral Ridge HOA — approx. $180/mo)"],
    ], col_widths=[2.0 * inch, 4.6 * inch]),
    sp(6),
]

# ── Section 10: Maintenance ───────────────────────────────────────────────────
story.append(sec("10", "Maintenance"))
story += [
    body(
        "Landlord shall be responsible for compliance with §83.51, Florida Statutes. "
        "Maintenance and repair responsibilities are allocated as follows "
        "(T = Tenant, L = Landlord):"
    ),
    sp(3),
    checklist_table([
        ("Roof",                  "L"),  ("Windows &amp; screens",    "T"),
        ("Exterior doors",        "L"),  ("Interior doors",           "T"),
        ("Floors (structural)",   "L"),  ("Floor coverings (carpet)", "T"),
        ("Exterior walls",        "L"),  ("Interior walls/paint",     "T"),
        ("Foundation",            "L"),  ("Ceilings",                 "T"),
        ("Plumbing (main lines)", "L"),  ("Plumbing (fixtures)",      "T"),
        ("Electrical (panel)",    "L"),  ("Electrical (outlets/fixtures)", "T"),
        ("HVAC system",           "L"),  ("HVAC filters",             "T"),
        ("Hot water heater",      "L"),  ("Running water",            "T"),
        ("Heating system",        "L"),  ("Cooling system",           "L"),
        ("Smoke detectors",       "T"),  ("Locks and keys",           "T"),
        ("Garbage removal",       "T"),  ("Outside receptacles",      "T"),
        ("Extermination (rodents/insects)", "T"), ("Pool/spa equipment", "L"),
        ("Pool chemicals/cleaning", "T"), ("Lawn/shrubbery",          "T"),
        ("Sprinkler system",      "T"),  ("Garage door/opener",       "T"),
        ("Driveway/walkway",      "T"),  ("Fence maintenance",        "T"),
    ]),
    sp(4),
    body(
        "<b>Tenant Repair Threshold:</b> Tenant is responsible for all repairs and maintenance "
        "costs under <b>$350.00 per occurrence</b>, regardless of cause, including items resulting "
        "from normal wear and tear or pre-existing conditions not disclosed at move-in. Tenant must "
        "obtain Landlord's written approval before engaging any contractor. Unauthorized repairs "
        "shall be at Tenant's sole expense and Tenant waives any right to offset repair costs against "
        "rent."
    ),
    body(
        "Tenant shall notify Landlord's Agent <b>Marco Reyes</b> at (305) 888-4401 of all "
        "maintenance requests in writing. Landlord shall address habitability-threatening conditions "
        "within 72 hours of written notice."
    ),
    sp(6),
]

# ── Section 11: Assignment ────────────────────────────────────────────────────
story.append(sec("11", "Assignment"))
story += [
    body(
        "Tenant may NOT assign this Lease or sublease all or any part of the Premises without "
        "first obtaining Landlord's prior written approval, which may be withheld at Landlord's "
        "sole discretion for any reason. Any listing of the Premises on Airbnb, VRBO, or any "
        "short-term rental platform constitutes a material breach and grounds for immediate "
        "termination, and Tenant shall be liable for all rental income earned plus "
        "<b>$5,000</b> in liquidated damages."
    ),
    sp(6),
]

# ── Section 12: Keys & Locks ──────────────────────────────────────────────────
story.append(sec("12", "Keys and Locks"))
story += [
    body(
        "Landlord shall furnish Tenant: <b>2 sets of house keys</b>, <b>1 mailbox key</b>, "
        "<b>2 garage door openers</b>, and <b>1 HOA pool access card</b>. "
        "Lost or unreturned items at end of Lease Term: $75 per key set, "
        "$125 per garage opener, $50 per access card. All items must be returned to "
        "Landlord's Agent at the office address upon vacating."
    ),
    sp(6),
]

# ── Section 13: Lead-Based Paint ──────────────────────────────────────────────
story.append(sec("13", "Lead-Based Paint Disclosure"))
story += [
    small(
        "<b>Lead Warning Statement:</b> Housing built before 1978 may contain lead-based paint. "
        "Lead from paint, paint chips, and dust can pose health hazards if not managed properly. "
        "Lead exposure is especially harmful to young children and pregnant women."
    ),
    small(
        "Landlord's Disclosure: The property at 3847 Coral Ridge Drive was built in <b>1994</b>. "
        "Landlord has no knowledge of lead-based paint or lead-based paint hazards in the dwelling. "
        "No records or reports pertaining to lead-based paint hazards are available."
    ),
    field("Landlord initials:", "M.R. _______", label_w=1.8 * inch, value_w=1.5 * inch),
    field("Tenant initials:",   "J.M. _______ / T.B. _______", label_w=1.8 * inch, value_w=2.5 * inch),
    sp(6),
]

# ── Section 14: Servicemember ─────────────────────────────────────────────────
story.append(sec("14", "Servicemember"))
story += [
    small(
        "If Tenant is a member of the United States Armed Forces on active duty or state active "
        "duty, or a member of the Florida National Guard or United States Reserve Forces, Tenant "
        "has rights to terminate the Lease as provided in Section 83.682, Florida Statutes."
    ),
    sp(6),
]

# ── Section 15: Landlord Access ───────────────────────────────────────────────
story.append(sec("15", "Landlord's Access to the Premises"))
story += [
    body(
        "Landlord or Landlord's Agent may enter the Premises under the following circumstances:"
    ),
    small("• At ANY TIME for the protection or preservation of the Premises."),
    small("• After reasonable notice at reasonable times for the purpose of repairing the Premises."),
    small(
        "• To inspect, repair, decorate, alter, or exhibit the Premises: with Tenant's consent; "
        "in case of emergency; when Tenant unreasonably withholds consent; or if Tenant is absent "
        "from the Premises for a period of at least one-half a rental installment period."
    ),
    body(
        "<b>Additional Landlord Right (Risky Clause):</b> Notwithstanding the above, Landlord "
        "reserves the right to enter the Premises at any time and for any reason with or without "
        "prior notice to conduct inspections, show the unit to prospective tenants or buyers, or "
        "for general access. Tenant's refusal to permit entry shall constitute a material breach."
    ),
    sp(6),
]

# ── Section 16: HOA ───────────────────────────────────────────────────────────
story.append(sec("16", "Homeowner's Association"))
story += [
    body(
        "This Lease is contingent upon Tenant receiving approval from the <b>Coral Ridge HOA</b>. "
        "The HOA application fee of $175.00 shall be paid by Tenant. If approval is not obtained "
        "prior to June 1, 2026, either party may terminate the Lease by written notice. "
        "Tenant agrees to comply with all HOA rules and regulations, including but not limited to "
        "parking rules, pool hours (7 AM – 10 PM), landscaping standards, and exterior "
        "modification restrictions. Violations resulting in HOA fines shall be paid by Tenant."
    ),
    sp(6),
]

# ── Section 17: Use of Premises ───────────────────────────────────────────────
story.append(sec("17", "Use of the Premises"))
story += [
    body(
        "Tenant shall use the Premises for residential purposes only. Tenant shall have exclusive "
        "use and right of possession. The Premises shall be used in compliance with all applicable "
        "state, county, and municipal laws, ordinances, HOA rules, and covenants and restrictions. "
        "Tenant may NOT paint or make any alterations or improvements without Landlord's prior "
        "written consent. Any improvements or alterations made by Tenant shall become Landlord's "
        "property. Upon vacating, Tenant must restore the Premises to original condition at "
        "Tenant's expense, including repainting all walls to the original color "
        "<b>even if no alterations were made</b>, and professional cleaning of all carpets, "
        "tile, and appliances regardless of condition."
    ),
    sp(6),
]

# ── Section 18: Risk of Loss / Insurance ──────────────────────────────────────
story.append(sec("18", "Risk of Loss / Insurance"))
story += [
    body(
        "Landlord and Tenant shall each be responsible for loss, damage, or injury caused by "
        "their own negligence or willful conduct. Tenant is <b>required</b> to carry renter's "
        "insurance with minimum coverage of <b>$50,000 personal property</b> and "
        "<b>$300,000 liability</b> throughout the Lease Term. Proof of insurance must be provided "
        "to Landlord within 48 hours of signing and upon each renewal. Failure to maintain "
        "insurance is a material breach. Landlord is not responsible for any loss of Tenant's "
        "personal property under any circumstances."
    ),
    sp(6),
]

# ── Section 19: Prohibited Acts by Landlord ───────────────────────────────────
story.append(sec("19", "Prohibited Acts by Landlord"))
story += [
    small(
        "Landlord is prohibited from taking certain actions as described in Section 83.67, "
        "Florida Statutes, including but not limited to: willful termination of utilities, "
        "removal of Tenant's belongings without legal process, or removal of doors, windows, or "
        "locks to force Tenant's departure."
    ),
    sp(6),
]

# ── Section 20: Casualty Damage ───────────────────────────────────────────────
story.append(sec("20", "Casualty Damage"))
story += [
    small(
        "If the Premises are damaged or destroyed other than by wrongful or negligent acts of "
        "Tenant, so that use is substantially impaired, Tenant may terminate the Lease within "
        "30 days after the damage and must immediately vacate. If Tenant vacates, Tenant is not "
        "liable for rent due after the date of termination."
    ),
    sp(6),
]

# ── Section 21: Defaults / Remedies ──────────────────────────────────────────
story.append(sec("21", "Defaults / Remedies"))
story += [
    small(
        "Should a party fail to fulfill their responsibilities under the Lease, refer to Part II, "
        "Chapter 83, Florida Residential Landlord and Tenant Act. "
        "<b>Attorney's Fees (Risky Clause):</b> In any legal action arising from this Lease, "
        "Tenant shall pay ALL of Landlord's attorney's fees, court costs, and legal expenses "
        "regardless of which party prevails. Tenant waives any right to recover attorney's fees "
        "from Landlord even if Tenant is the prevailing party."
    ),
    sp(6),
]

# ── Section 22: Subordination ─────────────────────────────────────────────────
story.append(sec("22", "Subordination"))
story += [
    small(
        "This Lease is automatically subordinate to the lien of any mortgage encumbering the "
        "fee title to the Premises from time to time."
    ),
    sp(6),
]

# ── Section 23: Liens ─────────────────────────────────────────────────────────
story.append(sec("23", "Liens"))
story += [
    small(
        "THE INTEREST OF THE LANDLORD SHALL NOT BE SUBJECT TO LIENS FOR IMPROVEMENTS MADE BY "
        "THE TENANT as provided in §713.10, Florida Statutes. Tenant shall notify all parties "
        "performing work on the Premises at Tenant's request that this Lease does not allow any "
        "liens to attach to Landlord's interest."
    ),
    sp(6),
]

# ── Section 24: Renewal / Extension ──────────────────────────────────────────
story.append(sec("24", "Renewal / Extension"))
story += [
    body(
        "This Lease can be renewed or extended ONLY by a written agreement signed by both parties; "
        "the term of a renewal, together with the original Lease Term, may not exceed one year. "
        "<b>Non-Renewal Notice (Risky Clause):</b> If Tenant wishes to vacate at the end of the "
        "Lease Term, Tenant must provide written notice of non-renewal at least <b>90 days</b> "
        "prior to the expiration date, delivered via <b>certified mail only</b>. Email or verbal "
        "notice shall not be deemed valid. Failure to provide timely notice shall result in "
        "automatic holdover tenancy at <b>$6,400/month</b> (double the monthly rent rate)."
    ),
    sp(6),
]

# ── Section 25: Tenant's Telephone Number ─────────────────────────────────────
story.append(sec("25", "Tenant's Telephone Number"))
story += [
    small(
        "Tenant shall, within 5 business days of obtaining telephone services at the Premises, "
        "send written notice to Landlord of Tenant's telephone numbers."
    ),
    sp(6),
]

# ── Section 26: Attorney's Fees ───────────────────────────────────────────────
story.append(sec("26", "Attorneys' Fees"))
story += [
    small(
        "In any lawsuit brought to enforce the Lease or under applicable law, the party in whose "
        "favor a judgment or decree has been rendered may recover reasonable court costs, including "
        "attorneys' fees, from the non-prevailing party."
    ),
    sp(6),
]

# ── Section 27: Miscellaneous ─────────────────────────────────────────────────
story.append(sec("27", "Miscellaneous"))
story += [
    small("• Time is of the essence of the performance of each party's obligations under the Lease."),
    small(
        "• The agreements contained in the Lease set forth the complete understanding of the parties "
        "and may not be changed or terminated orally."
    ),
    small(
        "• All questions concerning the Lease shall be determined pursuant to the laws of Florida."
    ),
    small(
        "• <b>Dispute Resolution (Risky Clause):</b> All disputes arising from this Lease must be "
        "resolved through <b>binding arbitration</b> administered by the American Arbitration "
        "Association. Tenant waives the right to a jury trial. Arbitration costs shall be borne "
        "solely by Tenant regardless of outcome."
    ),
    small(
        "• <b>RADON GAS DISCLOSURE:</b> Radon is a naturally occurring radioactive gas that, when "
        "accumulated in a building in sufficient quantities, may present health risks. Levels of "
        "radon that exceed federal and state guidelines have been found in buildings in Florida. "
        "Additional information may be obtained from your county health department."
    ),
    sp(6),
]

# ── Section 28: Brokers' Commission ──────────────────────────────────────────
story.append(sec("28", "Brokers' Commission"))
story += [
    small(
        "The brokerage company below will be paid the commission set forth herein by Landlord: "
        "Marco Reyes, Sunrise Realty Group LLC — Commission: One month's rent ($3,200.00)."
    ),
    sp(6),
]

# ── Section 29: Tenant's Personal Property ────────────────────────────────────
story.append(sec("29", "Tenant's Personal Property"))
story += [
    small(
        "BY SIGNING THIS LEASE, TENANT AGREES THAT UPON SURRENDER, ABANDONMENT, OR RECOVERY "
        "OF POSSESSION OF THE DWELLING UNIT DUE TO THE DEATH OF THE LAST REMAINING TENANT, "
        "AS PROVIDED BY CHAPTER 83, FLORIDA STATUTES, THE LANDLORD SHALL NOT BE LIABLE OR "
        "RESPONSIBLE FOR STORAGE OR DISPOSITION OF TENANT'S PERSONAL PROPERTY. "
        "Tenant initials: J.M. _______ / T.B. _______"
    ),
    sp(10), hr(1),
]

# ── Signatures ────────────────────────────────────────────────────────────────
story.append(sec("", "Signatures"))
story.append(sp(6))

sig_data = [
    [Paragraph("LANDLORD", section_style), Paragraph("TENANT", section_style), Paragraph("CO-TENANT", section_style)],
    [sp(18), sp(18), sp(18)],
    [
        Paragraph("_" * 32, body_style),
        Paragraph("_" * 32, body_style),
        Paragraph("_" * 32, body_style),
    ],
    [
        Paragraph("Sunrise Realty Group LLC", small_style),
        Paragraph("Jordan Miller", small_style),
        Paragraph("Taylor Brooks", small_style),
    ],
    [
        Paragraph("Authorized Representative", small_style),
        Paragraph("Tenant", small_style),
        Paragraph("Co-Tenant", small_style),
    ],
    [
        Paragraph("Date: June 1, 2026", small_style),
        Paragraph("Date: _______________", small_style),
        Paragraph("Date: _______________", small_style),
    ],
]
sig_table = Table(sig_data, colWidths=[2.2 * inch, 2.2 * inch, 2.2 * inch])
sig_table.setStyle(TableStyle([
    ("FONTSIZE",  (0, 0), (-1, -1), 9),
    ("TOPPADDING",(0, 0), (-1, -1), 4),
    ("VALIGN",    (0, 0), (-1, -1), "BOTTOM"),
    ("LINEBEFORE",(1, 0), (1, -1),  0.5, colors.HexColor("#cccccc")),
    ("LINEBEFORE",(2, 0), (2, -1),  0.5, colors.HexColor("#cccccc")),
]))
story.append(sig_table)

# ── Early Termination Addendum ────────────────────────────────────────────────
story += [PageBreak()]
story += [
    Paragraph("EARLY TERMINATION FEE / LIQUIDATED DAMAGES ADDENDUM", title_style),
    Paragraph("Addendum to Residential Lease dated June 1, 2026", subtitle_style),
    sp(8), hr(),
    body(
        "[X] Tenant agrees, as provided in the rental agreement, to pay <b>$6,400.00</b> "
        "(equal to 2 months' rent) as liquidated damages or an early termination fee if Tenant "
        "elects to terminate the rental agreement, and Landlord waives the right to seek "
        "additional rent beyond the month in which Landlord retakes possession."
    ),
    body(
        "[ ] Tenant does not agree to liquidated damages or an early termination fee, and "
        "acknowledges that Landlord may seek damages as provided by law."
    ),
    body(
        "<b>Additional Early Termination Terms (Risky Clause):</b> Notwithstanding the above, "
        "if Tenant terminates this Lease before the End Date for ANY reason — including job "
        "relocation, family emergency, or medical necessity — Tenant shall also be liable for: "
        "(a) all remaining rent due through the end of the Lease Term; AND (b) all costs incurred "
        "by Landlord in re-renting the unit, including advertising, cleaning, and agent "
        "commissions. Written notice of at least <b>90 days</b> is required prior to early "
        "departure. No exceptions shall be made regardless of circumstances."
    ),
    sp(20),
]

# Addendum signatures
add_sig = Table(sig_data, colWidths=[2.2 * inch, 2.2 * inch, 2.2 * inch])
add_sig.setStyle(TableStyle([
    ("FONTSIZE",  (0, 0), (-1, -1), 9),
    ("TOPPADDING",(0, 0), (-1, -1), 4),
    ("VALIGN",    (0, 0), (-1, -1), "BOTTOM"),
]))
story.append(add_sig)

story += [
    sp(20), hr(),
    Paragraph(
        "■ FOR TESTING PURPOSES ONLY — This is a fictitious lease agreement generated for "
        "software development and AI model testing. All names, addresses, and financial figures "
        "are entirely fabricated. No legal advice is expressed or implied.",
        footer_style,
    ),
]

# ── Build ─────────────────────────────────────────────────────────────────────
doc.build(story)
print(f"Generated: {os.path.abspath(OUTPUT)}")
