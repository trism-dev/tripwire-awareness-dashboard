from tripwire.fips import country_name
from tripwire.gdelt.cameo import event_description


def test_fips_names_are_fips_not_iso():
    assert country_name("UP") == "Ukraine"  # ISO would be UA
    assert country_name("US") == "United States"
    assert country_name("GM") == "Germany"  # ISO would be DE


def test_fips_codes_missing_from_gdelt_file_are_supplied():
    assert country_name("RB") == "Serbia"
    assert "Ocean" in country_name("OC")


def test_unknown_or_missing_country():
    assert country_name("ZZ") == "ZZ"
    assert country_name(None) == "Unknown"
    assert country_name("") == "Unknown"


def test_cameo_exact_codes_keep_leading_zeros():
    assert event_description("010") == "Make statement, not specified below"
    assert event_description("14") == "PROTEST"


def test_cameo_missing_code_falls_back_to_parent_and_says_so():
    # 1213 is in GDELT's event data but not in its lookup file; 121 is.
    assert event_description("1213") == event_description("121") + " (general)"


def test_cameo_garbage_codes():
    assert event_description("---") == "Unknown event type"
    assert event_description(None) == "Unknown event type"
    assert event_description("") == "Unknown event type"


def test_cameo_missing_value_from_pandas_is_not_a_crash():
    assert event_description(float("nan")) == "Unknown event type"
