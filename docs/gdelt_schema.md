# GDELT 2.0 Events: column reference

Source: GDELT Event Codebook V2.0 (https://www.gdeltproject.org/). Files are tab-delimited, no header, **61 columns**, despite the `.CSV` extension. Verified against a live export on 2026-10-04 (534 rows, all 61 fields).

| # | Column | Parsed as |
|---|---|---|
| 0 | `GLOBALEVENTID` | int (nullable) |
| 1 | `SQLDATE` | date |
| 2 | `MonthYear` | text |
| 3 | `Year` | text |
| 4 | `FractionDate` | text |
| 5 | `Actor1Code` | text |
| 6 | `Actor1Name` | text |
| 7 | `Actor1CountryCode` | text |
| 8 | `Actor1KnownGroupCode` | text |
| 9 | `Actor1EthnicCode` | text |
| 10 | `Actor1Religion1Code` | text |
| 11 | `Actor1Religion2Code` | text |
| 12 | `Actor1Type1Code` | text |
| 13 | `Actor1Type2Code` | text |
| 14 | `Actor1Type3Code` | text |
| 15 | `Actor2Code` | text |
| 16 | `Actor2Name` | text |
| 17 | `Actor2CountryCode` | text |
| 18 | `Actor2KnownGroupCode` | text |
| 19 | `Actor2EthnicCode` | text |
| 20 | `Actor2Religion1Code` | text |
| 21 | `Actor2Religion2Code` | text |
| 22 | `Actor2Type1Code` | text |
| 23 | `Actor2Type2Code` | text |
| 24 | `Actor2Type3Code` | text |
| 25 | `IsRootEvent` | int (nullable) |
| 26 | `EventCode` | text |
| 27 | `EventBaseCode` | text |
| 28 | `EventRootCode` | text |
| 29 | `QuadClass` | int (nullable) |
| 30 | `GoldsteinScale` | float |
| 31 | `NumMentions` | int (nullable) |
| 32 | `NumSources` | int (nullable) |
| 33 | `NumArticles` | int (nullable) |
| 34 | `AvgTone` | float |
| 35 | `Actor1Geo_Type` | int (nullable) |
| 36 | `Actor1Geo_FullName` | text |
| 37 | `Actor1Geo_CountryCode` | text |
| 38 | `Actor1Geo_ADM1Code` | text |
| 39 | `Actor1Geo_ADM2Code` | text |
| 40 | `Actor1Geo_Lat` | text |
| 41 | `Actor1Geo_Long` | text |
| 42 | `Actor1Geo_FeatureID` | text |
| 43 | `Actor2Geo_Type` | int (nullable) |
| 44 | `Actor2Geo_FullName` | text |
| 45 | `Actor2Geo_CountryCode` | text |
| 46 | `Actor2Geo_ADM1Code` | text |
| 47 | `Actor2Geo_ADM2Code` | text |
| 48 | `Actor2Geo_Lat` | text |
| 49 | `Actor2Geo_Long` | text |
| 50 | `Actor2Geo_FeatureID` | text |
| 51 | `ActionGeo_Type` | int (nullable) |
| 52 | `ActionGeo_FullName` | text |
| 53 | `ActionGeo_CountryCode` | text |
| 54 | `ActionGeo_ADM1Code` | text |
| 55 | `ActionGeo_ADM2Code` | text |
| 56 | `ActionGeo_Lat` | float |
| 57 | `ActionGeo_Long` | float |
| 58 | `ActionGeo_FeatureID` | text |
| 59 | `DATEADDED` | UTC timestamp |
| 60 | `SOURCEURL` | text |

Notes: CAMEO and FIPS codes stay text (`"013"` keeps its zero). Empty fields become NULL. Country codes are FIPS 10-4, not ISO.
