# DAX: Mining Operations Dashboard

Create a table called **`_Measures`** (Enter data → one empty column → delete the column afterwards) and keep all measures there.
The folder names below are the **Display folder** values (Model view → Properties).

---

## 1. Date table (Modeling → New table)

```dax
dim_date =
ADDCOLUMNS (
    CALENDAR ( DATE ( 2025, 1, 1 ), DATE ( 2026, 6, 30 ) ),
    "Year", YEAR ( [Date] ),
    "Quarter", "Q" & QUARTER ( [Date] ),
    "Year Quarter", YEAR ( [Date] ) & "-Q" & QUARTER ( [Date] ),
    "Month Number", MONTH ( [Date] ),
    "Month", FORMAT ( [Date], "MMM" ),
    "Year Month", FORMAT ( [Date], "YYYY-MM" ),
    "Month Start", DATE ( YEAR ( [Date] ), MONTH ( [Date] ), 1 ),
    "Days In Month", DAY ( EOMONTH ( [Date], 0 ) ),
    "Week Start", [Date] - WEEKDAY ( [Date], 2 ) + 1
)
```
Then: **Mark as date table** → `Date`. Sort `Month` by `Month Number`.

## 2. Relationships (all single direction, one-to-many)

| From (one) | To (many) |
|---|---|
| `dim_date[Date]` | `fact_production_shift[date]` |
| `dim_date[Date]` | `fact_mine_plan_monthly[month_start]` |
| `dim_date[Date]` | `fact_equipment_daily[date]` |
| `dim_date[Date]` | `fact_downtime_events[start_date]` |
| `dim_date[Date]` | `fact_assays[sample_date]` |
| `dim_pit[pit_id]` | `fact_production_shift[pit_id]`, `fact_mine_plan_monthly[pit_id]`, `fact_assays[pit_id]` |
| `dim_equipment[equipment_id]` | `fact_equipment_daily[equipment_id]`, `fact_downtime_events[equipment_id]` |
| `dim_crm[crm_id]` | `fact_assays[crm_id]` |

---

## 3. Production (folder: `1 Production`)

```dax
Ore Mined (t) = SUM ( fact_production_shift[ore_t] )

Waste Mined (t) = SUM ( fact_production_shift[waste_t] )

Total Material (t) = [Ore Mined (t)] + [Waste Mined (t)]

Strip Ratio = DIVIDE ( [Waste Mined (t)], [Ore Mined (t)] )

-- tonnage-weighted, never AVERAGE(grade)
Head Grade (g/t) =
DIVIDE (
    SUMX ( fact_production_shift, fact_production_shift[ore_t] * fact_production_shift[au_grade_gpt] ),
    [Ore Mined (t)]
)

Contained Gold (oz) =
DIVIDE (
    SUMX ( fact_production_shift, fact_production_shift[ore_t] * fact_production_shift[au_grade_gpt] ),
    31.1035
)

Avg Daily Material (t) = AVERAGEX ( VALUES ( dim_date[Date] ), [Total Material (t)] )

Avg Daily Material - Weather Days (t) =
CALCULATE ( [Avg Daily Material (t)], fact_production_shift[weather_delay_flag] = 1 )

Avg Daily Material - Normal Days (t) =
CALCULATE ( [Avg Daily Material (t)], fact_production_shift[weather_delay_flag] = 0 )

Ore Mined PY (t) = CALCULATE ( [Ore Mined (t)], SAMEPERIODLASTYEAR ( dim_date[Date] ) )

Ore Mined YoY % = DIVIDE ( [Ore Mined (t)] - [Ore Mined PY (t)], [Ore Mined PY (t)] )
```

## 4. Plan vs actual (folder: `2 Plan`)

The plan is monthly. These measures **prorate** it by the number of selected days in each month,
so "plan to date" is correct for any date range. The plan has no shift, so a shift filter does not change it.

```dax
Plan Ore (t) =
SUMX (
    VALUES ( dim_date[Month Start] ),
    VAR m = dim_date[Month Start]
    VAR DaysSelected = CALCULATE ( COUNTROWS ( dim_date ) )
    VAR DaysInMonth = DAY ( EOMONTH ( m, 0 ) )
    VAR MonthPlan =
        CALCULATE (
            SUM ( fact_mine_plan_monthly[plan_ore_t] ),
            REMOVEFILTERS ( dim_date ),
            dim_date[Month Start] = m
        )
    RETURN MonthPlan * DIVIDE ( DaysSelected, DaysInMonth )
)

Plan Waste (t) =
SUMX (
    VALUES ( dim_date[Month Start] ),
    VAR m = dim_date[Month Start]
    VAR Share = DIVIDE ( CALCULATE ( COUNTROWS ( dim_date ) ), DAY ( EOMONTH ( m, 0 ) ) )
    RETURN
        Share * CALCULATE ( SUM ( fact_mine_plan_monthly[plan_waste_t] ), REMOVEFILTERS ( dim_date ), dim_date[Month Start] = m )
)

Plan Contained Gold (oz) =
SUMX (
    VALUES ( dim_date[Month Start] ),
    VAR m = dim_date[Month Start]
    VAR Share = DIVIDE ( CALCULATE ( COUNTROWS ( dim_date ) ), DAY ( EOMONTH ( m, 0 ) ) )
    RETURN
        Share
            * CALCULATE (
                SUMX ( fact_mine_plan_monthly, fact_mine_plan_monthly[plan_ore_t] * fact_mine_plan_monthly[plan_au_grade_gpt] ),
                REMOVEFILTERS ( dim_date ),
                dim_date[Month Start] = m
            )
) / 31.1035

Plan Grade (g/t) = DIVIDE ( [Plan Contained Gold (oz)] * 31.1035, [Plan Ore (t)] )

Ore Plan Attainment % = DIVIDE ( [Ore Mined (t)], [Plan Ore (t)] )

Gold Plan Attainment % = DIVIDE ( [Contained Gold (oz)], [Plan Contained Gold (oz)] )

Ore Variance to Plan (t) = [Ore Mined (t)] - [Plan Ore (t)]

Gold Variance to Plan (oz) = [Contained Gold (oz)] - [Plan Contained Gold (oz)]

Grade Variance % = DIVIDE ( [Head Grade (g/t)] - [Plan Grade (g/t)], [Plan Grade (g/t)] )

-- for conditional formatting: green >= 100%, amber >= 95%, red below
Attainment Color =
SWITCH (
    TRUE (),
    [Ore Plan Attainment %] >= 1, "#16A34A",
    [Ore Plan Attainment %] >= 0.95, "#F59E0B",
    "#DC2626"
)
```

## 5. Fleet (folder: `3 Fleet`)

```dax
Scheduled Hours = SUM ( fact_equipment_daily[scheduled_h] )

Operating Hours = SUM ( fact_equipment_daily[operating_h] )

Standby Hours = SUM ( fact_equipment_daily[standby_h] )

Planned Downtime Hours = SUM ( fact_equipment_daily[planned_down_h] )

Unplanned Downtime Hours = SUM ( fact_equipment_daily[unplanned_down_h] )

Available Hours = [Scheduled Hours] - [Planned Downtime Hours] - [Unplanned Downtime Hours]

Physical Availability % = DIVIDE ( [Available Hours], [Scheduled Hours] )

Use of Availability % = DIVIDE ( [Operating Hours], [Available Hours] )

Effective Utilization % = DIVIDE ( [Operating Hours], [Scheduled Hours] )

Tonnes Hauled = SUM ( fact_equipment_daily[tonnes_hauled] )

Truck Loads = SUM ( fact_equipment_daily[loads] )

Avg Payload (t) = DIVIDE ( [Tonnes Hauled], [Truck Loads] )

Truck Productivity (t/op h) =
DIVIDE ( [Tonnes Hauled], CALCULATE ( [Operating Hours], dim_equipment[equipment_type] = "Haul Truck" ) )

Metres Drilled = SUM ( fact_equipment_daily[metres_drilled] )

Fuel (L) = SUM ( fact_equipment_daily[fuel_l] )

-- fleet fuel is not split by pit: use without a pit filter
Fuel per Tonne (L/t) = DIVIDE ( [Fuel (L)], [Total Material (t)] )
```

## 6. Downtime events (folder: `4 Downtime`)

```dax
Downtime Hours = SUM ( fact_downtime_events[duration_h] )

Breakdowns =
CALCULATE ( COUNTROWS ( fact_downtime_events ), fact_downtime_events[downtime_type] = "Unplanned" )

Breakdown Hours =
CALCULATE ( [Downtime Hours], fact_downtime_events[downtime_type] = "Unplanned" )

MTBF (h) = DIVIDE ( [Operating Hours], [Breakdowns] )

MTTR (h) = DIVIDE ( [Breakdown Hours], [Breakdowns] )

-- Pareto line: put downtime category on the axis, [Downtime Hours] as columns and this as the line
Downtime Cumulative % =
VAR CurrentHours = [Downtime Hours]
VAR Categories =
    ADDCOLUMNS ( ALLSELECTED ( fact_downtime_events[category] ), "@hours", [Downtime Hours] )
VAR Cumulative = SUMX ( FILTER ( Categories, [@hours] >= CurrentHours ), [@hours] )
RETURN DIVIDE ( Cumulative, SUMX ( Categories, [@hours] ) )

Equipment Rank (Breakdown Hours) =
RANKX ( ALLSELECTED ( dim_equipment[equipment_id] ), [Breakdown Hours],, DESC, DENSE )

-- Pareto of unplanned downtime only (planned maintenance is excluded)
Breakdown Cumulative % =
VAR CurrentHours = [Breakdown Hours]
VAR Categories =
    FILTER (
        ADDCOLUMNS ( ALLSELECTED ( fact_downtime_events[category] ), "@hours", [Breakdown Hours] ),
        NOT ISBLANK ( [@hours] )
    )
VAR Cumulative = SUMX ( FILTER ( Categories, [@hours] >= CurrentHours ), [@hours] )
RETURN IF ( NOT ISBLANK ( CurrentHours ), DIVIDE ( Cumulative, SUMX ( Categories, [@hours] ) ) )
```

## 7. QA/QC

### Calculated columns in `fact_assays`

`au_value` (number) and `below_detection` are created in Power Query (see `power_query.m`).

```dax
CRM Z-Score =
IF (
    fact_assays[sample_type] = "CRM",
    DIVIDE ( fact_assays[au_value] - RELATED ( dim_crm[certified_au_gpt] ), RELATED ( dim_crm[certified_sd_gpt] ) )
)

Parent Au (g/t) =
IF (
    fact_assays[sample_type] = "Field Duplicate",
    LOOKUPVALUE ( fact_assays[au_value], fact_assays[sample_id], fact_assays[parent_sample_id] )
)

QC Status =
SWITCH (
    fact_assays[sample_type],
    "CRM",
        SWITCH (
            TRUE (),
            ABS ( fact_assays[CRM Z-Score] ) > 3, "Fail",
            ABS ( fact_assays[CRM Z-Score] ) > 2, "Warning",
            "Pass"
        ),
    "Blank", IF ( fact_assays[au_value] > 0.05, "Fail", "Pass" ),
    "Field Duplicate",
        VAR a = fact_assays[Parent Au (g/t)]
        VAR b = fact_assays[au_value]
        VAR m = ( a + b ) / 2
        RETURN
            IF ( m < 0.1, "Not assessed", IF ( DIVIDE ( ABS ( a - b ), m ) > 0.2, "Fail", "Pass" ) ),
    BLANK ()
)
```

### Measures (folder: `5 QAQC`)

```dax
Samples = COUNTROWS ( fact_assays )

Primary Samples = CALCULATE ( [Samples], fact_assays[sample_type] = "Primary" )

QC Samples = CALCULATE ( [Samples], fact_assays[sample_type] <> "Primary" )

QC Insertion Rate % = DIVIDE ( [QC Samples], [Primary Samples] )

QC Assessed = CALCULATE ( [Samples], fact_assays[QC Status] IN { "Pass", "Warning", "Fail" } )

QC Failures = CALCULATE ( [Samples], fact_assays[QC Status] = "Fail" )

-- COALESCE: a period with assessed samples and no failures shows 0%, not blank
QC Failure Rate % = DIVIDE ( COALESCE ( [QC Failures], 0 ), [QC Assessed] )

CRM Failure Rate % = CALCULATE ( [QC Failure Rate %], fact_assays[sample_type] = "CRM" )

Blank Failure Rate % = CALCULATE ( [QC Failure Rate %], fact_assays[sample_type] = "Blank" )

Duplicate Failure Rate % = CALCULATE ( [QC Failure Rate %], fact_assays[sample_type] = "Field Duplicate" )

Avg Assay (g/t) = AVERAGE ( fact_assays[au_value] )

Max Assay (g/t) = MAX ( fact_assays[au_value] )

-- control-chart limits: select ONE CRM in a slicer
CRM Certified (g/t) = SELECTEDVALUE ( dim_crm[certified_au_gpt] )
CRM +2 SD = [CRM Certified (g/t)] + 2 * SELECTEDVALUE ( dim_crm[certified_sd_gpt] )
CRM -2 SD = [CRM Certified (g/t)] - 2 * SELECTEDVALUE ( dim_crm[certified_sd_gpt] )
CRM +3 SD = [CRM Certified (g/t)] + 3 * SELECTEDVALUE ( dim_crm[certified_sd_gpt] )
CRM -3 SD = [CRM Certified (g/t)] - 3 * SELECTEDVALUE ( dim_crm[certified_sd_gpt] )

Blank Limit (g/t) = 0.05

-- duplicate scatter: X = original sample, Y = duplicate (use with sample_id on Details)
Duplicate Original (g/t) = SUM ( fact_assays[Parent Au (g/t)] )

Duplicate Result (g/t) =
CALCULATE ( SUM ( fact_assays[au_value] ), fact_assays[sample_type] = "Field Duplicate" )
```

## 7b. Card subtitles and colors (folder: `9 Labels`)

```dax
KPI Ore Sub = FORMAT ( [Ore Plan Attainment %], "0.0%" ) & " of plan"

KPI Grade Sub = FORMAT ( [Grade Variance %], "+0.0%;-0.0%" ) & " vs plan grade"

KPI Gold Sub = FORMAT ( [Gold Plan Attainment %], "0.0%" ) & " of plan"

KPI Strip Sub = FORMAT ( [Total Material (t)] / 1e6, "0.00" ) & " Mt material moved"

KPI Availability Sub = "Use of availability " & FORMAT ( [Use of Availability %], "0.0%" )

KPI QC Sub = "CRM failures " & FORMAT ( [CRM Failure Rate %], "0.0%" )

KPI Weather Sub = FORMAT ( DIVIDE ( [Avg Daily Material - Weather Days (t)], [Avg Daily Material - Normal Days (t)] ) - 1, "+0%;-0%" ) & " vs normal days"

QC Fail Color =
SWITCH (
    TRUE (),
    ISBLANK ( [CRM Failure Rate %] ), BLANK (),
    [CRM Failure Rate %] >= 0.05, "#DC2626",
    [CRM Failure Rate %] >= 0.025, "#F59E0B",
    "#16A34A"
)
```

## 8. Titles that change with the filters

```dax
Title Overview =
"Mine overview · " & FORMAT ( MIN ( dim_date[Date] ), "d mmm yyyy" ) & " – " & FORMAT ( MAX ( dim_date[Date] ), "d mmm yyyy" )

Plan Status Text =
VAR v = [Ore Variance to Plan (t)]
RETURN
    IF ( v >= 0, "Ahead of plan by ", "Behind plan by " ) & FORMAT ( ABS ( v ), "#,0" ) & " t"
```
