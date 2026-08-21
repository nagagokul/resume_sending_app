from app.utils.normalize import (
    detect_remote_type,
    expand_compound_skill,
    infer_seniority,
    is_india_location,
    normalize_skill,
    normalize_title,
)


def test_normalize_skill_aliases():
    assert normalize_skill("Cpp") == "C++"
    assert normalize_skill("C Plus Plus") == "C++"
    assert normalize_skill("Linux OS") == "Linux"
    assert normalize_skill("multi-threading") == "Multithreading"
    assert normalize_skill("netconf") == "NETCONF"


def test_expand_c_cpp():
    assert expand_compound_skill("C/C++") == ["C", "C++"]


def test_normalize_title_and_seniority():
    assert "Software Engineer" in normalize_title("Software Development Engineer II")
    assert infer_seniority("Senior Software Engineer") == "SENIOR"
    assert infer_seniority("Staff Platform Engineer") == "STAFF"
    assert infer_seniority("SDE II") == "MID"


def test_location_helpers():
    assert is_india_location("Bangalore, India")
    assert is_india_location("Hyderabad")
    assert detect_remote_type("Remote - India") == "remote"
    assert detect_remote_type("Pune, India") == "onsite"
