// Power Query (M) - Mining Operations Dashboard
// ------------------------------------------------------------------------------
// 1. Create a parameter called DataFolder (Home > Manage Parameters > New), type Text,
//    value = the full path of the data folder, ending with a backslash, e.g.
//    C:\Portfolio\01-mining-operations-dashboard\data\
// 2. For each query: Home > New Source > Blank Query > Advanced Editor > paste.
// The CSV files use "." as the decimal separator, so every type change uses
// the "en-US" culture. This keeps numbers correct on a PC with Uzbek or Russian regional settings.
// ------------------------------------------------------------------------------


// ---------- fact_production_shift ----------
let
    Source = Csv.Document(File.Contents(DataFolder & "fact_production_shift.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"date", type date}, {"shift", type text}, {"pit_id", type text},
        {"ore_t", Int64.Type}, {"waste_t", Int64.Type}, {"au_grade_gpt", type number},
        {"weather_delay_flag", Int64.Type}}, "en-US")
in
    Typed


// ---------- fact_mine_plan_monthly ----------
let
    Source = Csv.Document(File.Contents(DataFolder & "fact_mine_plan_monthly.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"month_start", type date}, {"pit_id", type text}, {"plan_ore_t", Int64.Type},
        {"plan_waste_t", Int64.Type}, {"plan_au_grade_gpt", type number}}, "en-US")
in
    Typed


// ---------- fact_equipment_daily ----------
// loads / tonnes_hauled exist only for trucks and metres_drilled only for drills:
// empty cells become null, which is correct (not zero).
let
    Source = Csv.Document(File.Contents(DataFolder & "fact_equipment_daily.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    EmptyToNull = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, {"loads", "tonnes_hauled", "metres_drilled"}),
    Typed = Table.TransformColumnTypes(EmptyToNull, {
        {"date", type date}, {"equipment_id", type text}, {"scheduled_h", type number},
        {"operating_h", type number}, {"standby_h", type number}, {"planned_down_h", type number},
        {"unplanned_down_h", type number}, {"loads", Int64.Type}, {"tonnes_hauled", Int64.Type},
        {"metres_drilled", type number}, {"fuel_l", Int64.Type}}, "en-US")
in
    Typed


// ---------- fact_downtime_events ----------
let
    Source = Csv.Document(File.Contents(DataFolder & "fact_downtime_events.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"event_id", type text}, {"equipment_id", type text}, {"start_datetime", type datetime},
        {"end_datetime", type datetime}, {"duration_h", type number}, {"downtime_type", type text},
        {"category", type text}, {"description", type text}, {"work_order", type text}}, "en-US"),
    StartDate = Table.AddColumn(Typed, "start_date", each Date.From([start_datetime]), type date)
in
    StartDate


// ---------- fact_assays ----------
// The lab reports results below the detection limit as the text "<0.01".
// Convention: replace them with half the detection limit (0.005 g/t) and keep a flag.
let
    Source = Csv.Document(File.Contents(DataFolder & "fact_assays.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"sample_id", type text}, {"batch_id", type text}, {"sample_date", type date}, {"pit_id", type text},
        {"lab", type text}, {"sample_type", type text}, {"parent_sample_id", type text},
        {"crm_id", type text}, {"au_gpt", type text}}, "en-US"),
    EmptyToNull = Table.ReplaceValue(Typed, "", null, Replacer.ReplaceValue, {"parent_sample_id", "crm_id"}),
    BelowDetection = Table.AddColumn(EmptyToNull, "below_detection", each Text.StartsWith([au_gpt], "<"), type logical),
    AuValue = Table.AddColumn(BelowDetection, "au_value",
        each if [below_detection] then 0.005 else Number.From([au_gpt], "en-US"), type number),
    Removed = Table.RemoveColumns(AuValue, {"au_gpt"})
in
    Removed


// ---------- dim_pit ----------
let
    Source = Csv.Document(File.Contents(DataFolder & "dim_pit.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"pit_id", type text}, {"pit_name", type text}, {"ore_type", type text},
        {"start_date", type date}, {"avg_haul_distance_km", type number}}, "en-US")
in
    Typed


// ---------- dim_equipment ----------
let
    Source = Csv.Document(File.Contents(DataFolder & "dim_equipment.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    EmptyToNull = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, {"rated_payload_t"}),
    Typed = Table.TransformColumnTypes(EmptyToNull, {
        {"equipment_id", type text}, {"equipment_type", type text}, {"model", type text},
        {"rated_payload_t", Int64.Type}, {"manufacture_year", Int64.Type}, {"commissioned_date", type date}}, "en-US"),
    AgeGroup = Table.AddColumn(Typed, "age_group",
        each if [manufacture_year] <= 2017 then "2017 or older" else "2018 or newer", type text)
in
    AgeGroup


// ---------- dim_crm ----------
let
    Source = Csv.Document(File.Contents(DataFolder & "dim_crm.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"crm_id", type text}, {"certified_au_gpt", type number}, {"certified_sd_gpt", type number},
        {"description", type text}}, "en-US")
in
    Typed
