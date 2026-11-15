"""Generate the synthetic dataset for the Mining Operations Dashboard.

Everything here is fictional: a made-up open-pit gold mine with three pits,
a 31-unit mobile fleet and a grade-control sampling program.
The random seed is fixed, so every run produces exactly the same files.

Usage:
    python generate_data.py [output_dir]      (default: ../data)
"""
import csv
import math
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

random.seed(20250101)

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "data"
OUT.mkdir(parents=True, exist_ok=True)

START = date(2025, 1, 1)
END = date(2026, 6, 30)
DAYS = [START + timedelta(days=i) for i in range((END - START).days + 1)]
END_DT = datetime.combine(END + timedelta(days=1), datetime.min.time())


def write_csv(name, header, rows):
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"{name:<28}{len(rows):>8,} rows")


def lognormal_mean(mean, sigma):
    """Lognormal draw whose expected value is `mean`."""
    return random.lognormvariate(math.log(mean) - sigma * sigma / 2, sigma)


def month_start(d):
    return d.replace(day=1)


# --------------------------------------------------------------------------
# Pits
# --------------------------------------------------------------------------
PITS = [
    {"pit_id": "P1", "pit_name": "North Pit", "ore_type": "Oxide", "start": date(2025, 1, 1),
     "weight": 0.45, "strip": 3.2, "grade": 1.45, "haul_km": 2.8},
    {"pit_id": "P2", "pit_name": "South Pit", "ore_type": "Sulphide", "start": date(2025, 1, 1),
     "weight": 0.55, "strip": 5.4, "grade": 2.10, "haul_km": 3.6},
    {"pit_id": "P3", "pit_name": "East Pit", "ore_type": "Oxide", "start": date(2025, 7, 1),
     "weight": 0.24, "strip": 2.1, "grade": 0.95, "haul_km": 4.4},
]


def active_pits(d):
    return [p for p in PITS if d >= p["start"]]


# Seasonal effect on truck cycle times (snow, mud, heat).
SEASON = {1: 0.90, 2: 0.92, 3: 0.96, 4: 0.97, 5: 1.01, 6: 1.03,
          7: 1.04, 8: 1.04, 9: 1.02, 10: 1.00, 11: 0.96, 12: 0.92}


def weather_probability(d):
    if d.month in (12, 1, 2):
        return 0.09   # snow, fog
    if d.month in (3, 4, 5):
        return 0.11   # heavy rain
    if d.month in (10, 11):
        return 0.05
    return 0.02


WEATHER = {d: random.random() < weather_probability(d) for d in DAYS}

# --------------------------------------------------------------------------
# Equipment
# --------------------------------------------------------------------------
EQUIPMENT = []
for i in range(1, 21):
    commissioned = date(2026, 3, 1) if i >= 19 else START
    year = 2025 if i >= 19 else (2016 if i == 7 else random.randint(2015, 2022))
    EQUIPMENT.append({"equipment_id": f"HT-{i:02d}", "equipment_type": "Haul Truck", "model": "HT-150",
                      "rated_payload_t": 150, "year": year, "commissioned": commissioned})
for i in range(1, 5):
    EQUIPMENT.append({"equipment_id": f"EX-{i:02d}", "equipment_type": "Excavator", "model": "EX-350",
                      "rated_payload_t": "", "year": random.randint(2014, 2021), "commissioned": START})
for i in range(1, 3):
    EQUIPMENT.append({"equipment_id": f"LD-{i:02d}", "equipment_type": "Wheel Loader", "model": "WL-90",
                      "rated_payload_t": "", "year": random.randint(2016, 2022), "commissioned": START})
for i in range(1, 6):
    EQUIPMENT.append({"equipment_id": f"DR-{i:02d}", "equipment_type": "Drill Rig", "model": "DR-200",
                      "rated_payload_t": "", "year": random.randint(2015, 2023), "commissioned": START})

TYPE = {
    "Haul Truck":   {"pm_int": 250, "pm_dur": (9, 12),  "mtbf": 170, "standby": (2.0, 3.4), "fuel": (92, 6),   "idle_fuel": 14},
    "Excavator":    {"pm_int": 250, "pm_dur": (12, 16), "mtbf": 150, "standby": (1.6, 3.0), "fuel": (165, 10), "idle_fuel": 20},
    "Wheel Loader": {"pm_int": 250, "pm_dur": (7, 9),   "mtbf": 200, "standby": (3.0, 6.0), "fuel": (68, 5),   "idle_fuel": 9},
    "Drill Rig":    {"pm_int": 200, "pm_dur": (7, 9),   "mtbf": 120, "standby": (2.0, 4.0), "fuel": (48, 4),   "idle_fuel": 6},
}

# (category, weight, mean repair hours)
FAILURE_CATEGORIES = {
    "Haul Truck": [("Tyres", 0.24, 4), ("Hydraulics", 0.18, 6), ("Engine", 0.16, 14), ("Electrical", 0.15, 5),
                   ("Transmission", 0.10, 18), ("Structural", 0.05, 10), ("Other", 0.12, 3)],
    "Excavator": [("Hydraulics", 0.34, 7), ("Ground Engaging Tools", 0.18, 4), ("Engine", 0.14, 16),
                  ("Electrical", 0.14, 6), ("Structural", 0.08, 12), ("Other", 0.12, 3)],
    "Wheel Loader": [("Tyres", 0.22, 4), ("Hydraulics", 0.25, 6), ("Engine", 0.18, 12), ("Electrical", 0.15, 5),
                     ("Other", 0.20, 3)],
    "Drill Rig": [("Drill String", 0.32, 3), ("Hydraulics", 0.24, 6), ("Engine", 0.14, 12), ("Electrical", 0.14, 5),
                  ("Other", 0.16, 3)],
}
DESCRIPTIONS = {
    "Tyres": ["Tyre puncture", "Tyre sidewall damage", "Tyre change - worn tread"],
    "Hydraulics": ["Hydraulic hose burst", "Hydraulic pump failure", "Cylinder seal leak"],
    "Engine": ["Engine overheating", "Turbocharger failure", "Fuel injector fault"],
    "Electrical": ["Alternator failure", "Wiring harness fault", "Sensor / ECU fault"],
    "Transmission": ["Transmission clutch failure", "Final drive fault"],
    "Structural": ["Frame crack repair", "Body / tray repair"],
    "Ground Engaging Tools": ["Bucket tooth replacement", "Lip shroud replacement"],
    "Drill String": ["Drill bit change", "Drill rod replacement"],
    "Other": ["Operator-reported fault", "Fire suppression check", "Lights / camera fault"],
}

HT07_PROBLEM_FROM = date(2025, 9, 1)          # recurring hydraulic failures start here
EX02_MAJOR_FAILURE = date(2026, 2, 9)         # engine block crack, ~5 days down


def failure_rate(eq, d):
    rate = 1.0 / TYPE[eq["equipment_type"]]["mtbf"]
    if eq["year"] <= 2017:
        rate *= 1.3
    if eq["equipment_id"] == "HT-07" and d >= HT07_PROBLEM_FROM:
        rate *= 2.4
    return rate


def pick_failure(eq, d):
    cats = FAILURE_CATEGORIES[eq["equipment_type"]]
    if eq["equipment_id"] == "HT-07" and d >= HT07_PROBLEM_FROM and random.random() < 0.6:
        cat, mean = "Hydraulics", 7
    else:
        r = random.random() * sum(w for _, w, _ in cats)
        for cat, w, mean in cats:
            r -= w
            if r <= 0:
                break
    duration = min(max(lognormal_mean(mean, 0.6), 0.5), 72)
    return cat, random.choice(DESCRIPTIONS[cat]), duration


# --------------------------------------------------------------------------
# Fleet simulation (day by day)
# --------------------------------------------------------------------------
events = []            # downtime events
equipment_daily = {}   # (date, equipment_id) -> dict
carry = {}             # equipment_id -> [remaining_h, downtime_type]
op_since_pm = {eq["equipment_id"]: random.uniform(0, TYPE[eq["equipment_type"]]["pm_int"]) for eq in EQUIPMENT}
event_counter = 0


def new_event(eq, start_dt, duration, dtype, category, description):
    global event_counter
    event_counter += 1
    end_dt = start_dt + timedelta(hours=duration)
    if end_dt > END_DT:
        end_dt = END_DT
        duration = (end_dt - start_dt).total_seconds() / 3600
    events.append([f"DT-{event_counter:05d}", eq["equipment_id"], start_dt.strftime("%Y-%m-%d %H:%M"),
                   end_dt.strftime("%Y-%m-%d %H:%M"), round(duration, 2), dtype, category, description,
                   f"WO-{24000 + event_counter}"])


for d in DAYS:
    day_start = datetime.combine(d, datetime.min.time())
    for eq in EQUIPMENT:
        if d < eq["commissioned"]:
            continue
        eid, t = eq["equipment_id"], TYPE[eq["equipment_type"]]
        planned = unplanned = operating = 0.0
        clock = 0.0

        # 1) repairs carried over from previous days
        if eid in carry:
            remaining, dtype = carry.pop(eid)
            used = min(remaining, 24.0)
            if dtype == "Planned":
                planned += used
            else:
                unplanned += used
            clock = used
            if remaining > used:
                carry[eid] = [remaining - used, dtype]

        window = 24.0 - clock
        standby_target = random.uniform(*t["standby"]) + (random.uniform(4, 8) if WEATHER[d] else 0)
        standby = min(standby_target, window) * (window / 24.0)
        op_window = window - standby
        op_window_initial = max(op_window, 1e-9)
        forced_failure_at = 5.0 if (eid == "EX-02" and d == EX02_MAJOR_FAILURE) else None

        # 2) operate until the window closes, a failure happens or PM is due
        while op_window > 1e-6 and eid not in carry:
            to_pm = max(TYPE[eq["equipment_type"]]["pm_int"] - op_since_pm[eid], 0.0)
            if forced_failure_at is not None:
                ttf = max(forced_failure_at - operating, 0.0)
            else:
                ttf = random.expovariate(failure_rate(eq, d))
            step = min(ttf, to_pm, op_window)
            operating += step
            op_since_pm[eid] += step
            op_window -= step
            if op_window <= 1e-6 and step < min(ttf, to_pm):
                break

            # hour of day when the event starts (standby is spread over the day)
            event_clock = operating + planned + unplanned + standby * (operating / op_window_initial)
            start_dt = day_start + timedelta(hours=min(event_clock, 23.9))

            if forced_failure_at is not None and step == ttf:
                dtype, cat, desc, duration = "Unplanned", "Engine", "Engine block crack - major repair", 118.0
                forced_failure_at = None
            elif step == to_pm:
                dtype, cat, desc = "Planned", "Preventive Maintenance", f"{t['pm_int']}h PM service"
                duration = random.uniform(*t["pm_dur"])
                op_since_pm[eid] = 0.0
            else:
                dtype = "Unplanned"
                cat, desc, duration = pick_failure(eq, d)

            new_event(eq, start_dt, duration, dtype, cat, desc)
            used = min(duration, op_window)
            if dtype == "Planned":
                planned += used
            else:
                unplanned += used
            op_window -= used
            if duration > used:
                carry[eid] = [duration - used, dtype]

        standby = 24.0 - operating - planned - unplanned
        equipment_daily[(d, eid)] = {"operating": operating, "standby": standby,
                                     "planned": planned, "unplanned": unplanned}

# --------------------------------------------------------------------------
# Truck productivity, loading capacity and fuel
# --------------------------------------------------------------------------
production_rows, daily_rows = [], []
ex_rate, ld_rate = 1450, 520   # t per operating hour

for d in DAYS:
    pits = active_pits(d)
    avg_km = sum(p["haul_km"] * p["weight"] for p in pits) / sum(p["weight"] for p in pits)
    cycle_min = 3.5 + 1.2 + (avg_km * 2 / 22) * 60 + 2.5
    cycles_per_h = 60 / cycle_min * SEASON[d.month] * (0.85 if WEATHER[d] else 1.0)

    trucks = {}
    for eq in EQUIPMENT:
        if eq["equipment_type"] != "Haul Truck" or (d, eq["equipment_id"]) not in equipment_daily:
            continue
        op = equipment_daily[(d, eq["equipment_id"])]["operating"]
        loads = max(int(round(op * cycles_per_h * random.gauss(1, 0.05))), 0)
        payload = min(random.gauss(141, 4), 150)
        trucks[eq["equipment_id"]] = [loads, payload]

    truck_t = sum(l * p for l, p in trucks.values())
    loading_cap = sum(equipment_daily[(d, e["equipment_id"])]["operating"] * (ex_rate if e["equipment_type"] == "Excavator" else ld_rate)
                      for e in EQUIPMENT if e["equipment_type"] in ("Excavator", "Wheel Loader") and (d, e["equipment_id"]) in equipment_daily)
    if truck_t > loading_cap > 0:
        f = loading_cap / truck_t
        for v in trucks.values():
            v[0] = int(round(v[0] * f))
    total_material = sum(l * p for l, p in trucks.values())

    for eq in EQUIPMENT:
        key = (d, eq["equipment_id"])
        if key not in equipment_daily:
            continue
        h = equipment_daily[key]
        t = TYPE[eq["equipment_type"]]
        fuel = h["operating"] * max(random.gauss(*t["fuel"]), 0) + h["standby"] * t["idle_fuel"] * random.uniform(0.6, 1.0)
        loads = tonnes = metres = ""
        if eq["equipment_type"] == "Haul Truck":
            loads = trucks[eq["equipment_id"]][0]
            tonnes = round(loads * trucks[eq["equipment_id"]][1])
        elif eq["equipment_type"] == "Drill Rig":
            metres = round(h["operating"] * random.gauss(24, 2), 1)
        op, pl, un = round(h["operating"], 2), round(h["planned"], 2), round(h["unplanned"], 2)
        sb = round(24 - op - pl - un, 2)
        daily_rows.append([d.isoformat(), eq["equipment_id"], 24, op, sb, pl, un, loads, tonnes, metres, round(fuel)])

    # ---------------- allocate material to pits and shifts ----------------
    weights = {p["pit_id"]: p["weight"] * random.gauss(1, 0.08) for p in pits}
    wsum = sum(weights.values())
    months_from_start = (d.year - START.year) * 12 + d.month - 1
    for p in pits:
        material = total_material * weights[p["pit_id"]] / wsum
        strip = p["strip"] * random.gauss(1, 0.10)
        gfac = 1.0
        if p["pit_id"] == "P2" and date(2026, 1, 1) <= d <= date(2026, 3, 31):
            strip *= 1.12
            gfac = 0.86                                     # dilution in South Pit
        if p["pit_id"] == "P1":
            gfac = 1.05 - 0.10 * months_from_start / 17     # high-grade zone depleting
        if p["pit_id"] == "P3" and d < date(2025, 9, 1):
            gfac = 0.85 if d.month == 7 else 0.93           # ramp-up
        ore = material / (1 + strip)
        waste = material - ore
        day_frac = random.gauss(0.52, 0.02)
        for shift, frac in (("Day", day_frac), ("Night", 1 - day_frac)):
            grade = p["grade"] * gfac * lognormal_mean(1.0, 0.10)
            production_rows.append([d.isoformat(), shift, p["pit_id"], round(ore * frac), round(waste * frac),
                                    round(grade, 2), int(WEATHER[d])])

# --------------------------------------------------------------------------
# Monthly mine plan
# --------------------------------------------------------------------------
actual_month = {}
for r in production_rows:
    d = date.fromisoformat(r[0])
    key = (month_start(d), r[2])
    a = actual_month.setdefault(key, [0, 0])
    a[0] += r[3]
    a[1] += r[4]

plan_rows = []
pit_by_id = {p["pit_id"]: p for p in PITS}
for (m, pit_id), (ore, waste) in sorted(actual_month.items()):
    adjust = 1.0
    if pit_id == "P2" and date(2026, 1, 1) <= m <= date(2026, 3, 1):
        adjust *= 1.10          # plan did not expect the dilution
    if m == date(2026, 2, 1):
        adjust *= 1.07          # plan did not expect the EX-02 failure
    plan_ore = ore * adjust * random.gauss(1.035, 0.025)
    plan_waste = waste * random.gauss(1.02, 0.03)
    plan_grade = pit_by_id[pit_id]["grade"] * random.gauss(1, 0.02)
    if pit_id == "P3" and m < date(2025, 9, 1):
        plan_grade *= 0.92
    plan_rows.append([m.isoformat(), pit_id, int(round(plan_ore, -2)), int(round(plan_waste, -2)), round(plan_grade, 2)])

# --------------------------------------------------------------------------
# Grade-control sampling and QA/QC
# --------------------------------------------------------------------------
CRMS = [("CRM-A", 0.52, 0.025, "Low-grade oxide reference material", 0.30),
        ("CRM-B", 1.85, 0.070, "Medium-grade reference material", 0.45),
        ("CRM-C", 4.60, 0.160, "High-grade sulphide reference material", 0.25)]


def fmt_au(v):
    return "<0.01" if v < 0.01 else f"{v:.2f}"


pit_day_grade = {}
for r in production_rows:
    pit_day_grade.setdefault((r[0], r[2]), []).append(r[5])

assay_rows = []
sample_no = 0


def next_id():
    global sample_no
    sample_no += 1
    return f"GC-{sample_no:06d}"


for d in DAYS:
    for p in active_pits(d):
        lab = "Lab Alpha" if random.random() < 0.65 else "Lab Beta"
        batch = f"B{d:%y%m%d}-{p['pit_id']}"
        mean_grade = sum(pit_day_grade[(d.isoformat(), p["pit_id"])]) / 2
        n = random.randint(14, 22)
        if WEATHER[d]:
            n = int(n * 0.6)
        blank_pos = random.randint(1, n)
        contamination = lab == "Lab Alpha" and date(2025, 11, 10) <= d <= date(2025, 11, 21)
        lab_bias = lab == "Lab Beta" and date(2026, 3, 1) <= d <= date(2026, 4, 30)

        for i in range(1, n + 1):
            true_v = lognormal_mean(mean_grade, 0.55)
            sid = next_id()
            assay_rows.append([sid, batch, d.isoformat(), p["pit_id"], lab, "Primary", "", "", fmt_au(true_v)])

            if i % 15 == 0:                                     # field duplicate
                sigma = 0.45 if random.random() < 0.02 else 0.09
                assay_rows.append([next_id(), batch, d.isoformat(), p["pit_id"], lab, "Field Duplicate", sid, "",
                                   fmt_au(true_v * lognormal_mean(1.0, sigma))])
            if i == blank_pos:                                  # blank
                v = random.uniform(0.06, 0.20) if (contamination and random.random() < 0.7) else \
                    (random.uniform(0, 0.02) if random.random() < 0.3 else 0.005)
                assay_rows.append([next_id(), batch, d.isoformat(), p["pit_id"], lab, "Blank", "", "", fmt_au(v)])
            if i % 20 == 0 or i == n and n < 20:                # certified reference material
                r = random.random()
                for crm_id, cert, sd, _, w in CRMS:
                    r -= w
                    if r <= 0:
                        break
                if random.random() < 0.005:                     # label swap - gross error
                    other = random.choice([c for c in CRMS if c[0] != crm_id])
                    v = other[1] + random.gauss(0, other[2])
                else:
                    v = cert + random.gauss(2.3 * sd if lab_bias else 0, 0.8 * sd if lab_bias else sd)
                assay_rows.append([next_id(), batch, d.isoformat(), p["pit_id"], lab, "CRM", "", crm_id, fmt_au(v)])

# --------------------------------------------------------------------------
# Write files
# --------------------------------------------------------------------------
write_csv("dim_pit.csv", ["pit_id", "pit_name", "ore_type", "start_date", "avg_haul_distance_km"],
          [[p["pit_id"], p["pit_name"], p["ore_type"], p["start"].isoformat(), p["haul_km"]] for p in PITS])
write_csv("dim_equipment.csv", ["equipment_id", "equipment_type", "model", "rated_payload_t", "manufacture_year", "commissioned_date"],
          [[e["equipment_id"], e["equipment_type"], e["model"], e["rated_payload_t"], e["year"], e["commissioned"].isoformat()] for e in EQUIPMENT])
write_csv("dim_crm.csv", ["crm_id", "certified_au_gpt", "certified_sd_gpt", "description"],
          [[c[0], c[1], c[2], c[3]] for c in CRMS])
write_csv("fact_production_shift.csv", ["date", "shift", "pit_id", "ore_t", "waste_t", "au_grade_gpt", "weather_delay_flag"],
          production_rows)
write_csv("fact_mine_plan_monthly.csv", ["month_start", "pit_id", "plan_ore_t", "plan_waste_t", "plan_au_grade_gpt"], plan_rows)
write_csv("fact_equipment_daily.csv", ["date", "equipment_id", "scheduled_h", "operating_h", "standby_h", "planned_down_h",
                                       "unplanned_down_h", "loads", "tonnes_hauled", "metres_drilled", "fuel_l"], daily_rows)
write_csv("fact_downtime_events.csv", ["event_id", "equipment_id", "start_datetime", "end_datetime", "duration_h",
                                       "downtime_type", "category", "description", "work_order"], events)
write_csv("fact_assays.csv", ["sample_id", "batch_id", "sample_date", "pit_id", "lab", "sample_type",
                              "parent_sample_id", "crm_id", "au_gpt"], assay_rows)
