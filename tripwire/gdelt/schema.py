"""The 61 columns of a GDELT 2.0 Events export, in file order (Event Codebook V2.0)."""

_ACTOR_FIELDS = [
    "Code",
    "Name",
    "CountryCode",
    "KnownGroupCode",
    "EthnicCode",
    "Religion1Code",
    "Religion2Code",
    "Type1Code",
    "Type2Code",
    "Type3Code",
]
_GEO_FIELDS = [
    "Type",
    "FullName",
    "CountryCode",
    "ADM1Code",
    "ADM2Code",
    "Lat",
    "Long",
    "FeatureID",
]

COLUMNS = (
    ["GLOBALEVENTID", "SQLDATE", "MonthYear", "Year", "FractionDate"]
    + [f"Actor1{f}" for f in _ACTOR_FIELDS]
    + [f"Actor2{f}" for f in _ACTOR_FIELDS]
    + ["IsRootEvent", "EventCode", "EventBaseCode", "EventRootCode", "QuadClass"]
    + ["GoldsteinScale", "NumMentions", "NumSources", "NumArticles", "AvgTone"]
    + [f"Actor1Geo_{f}" for f in _GEO_FIELDS]
    + [f"Actor2Geo_{f}" for f in _GEO_FIELDS]
    + [f"ActionGeo_{f}" for f in _GEO_FIELDS]
    + ["DATEADDED", "SOURCEURL"]
)

# Everything is read as text first. Only these are cast afterwards.
# CAMEO codes (EventCode etc.) and FIPS codes are deliberately NOT here: "014" must stay "014".
INT_COLUMNS = [
    "GLOBALEVENTID",
    "IsRootEvent",
    "QuadClass",
    "NumMentions",
    "NumSources",
    "NumArticles",
    "Actor1Geo_Type",
    "Actor2Geo_Type",
    "ActionGeo_Type",
]
FLOAT_COLUMNS = [
    "GoldsteinScale",
    "AvgTone",
    "ActionGeo_Lat",
    "ActionGeo_Long",
]
