from types import SimpleNamespace

from app.services.matching.engine import classify_score, compute_match


def _job(**kwargs):
    defaults = dict(
        title="Senior C++ Software Engineer",
        normalized_title="Senior C++ Software Engineer",
        description="Linux systems networking NETCONF device drivers multithreading C++ Python",
        requirements=["C++", "Linux", "Networking", "NETCONF", "Multithreading"],
        location="Bangalore, India",
        remote_type="hybrid",
        is_india=True,
        seniority="SENIOR",
        salary=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_classify_bands():
    assert classify_score(95) == "excellent"
    assert classify_score(85) == "strong"
    assert classify_score(75) == "possible"
    assert classify_score(65) == "weak"
    assert classify_score(40) == "skip"


def test_strong_systems_match():
    result = compute_match(
        candidate_skills={"C++", "C", "Linux", "Networking", "NETCONF", "Multithreading", "Python"},
        candidate_titles=["Senior Software Engineer", "Software Engineer"],
        candidate_text="C++ Linux networking NETCONF device drivers optical systems",
        candidate_location="Bangalore",
        preferences={"seniority": "SENIOR", "target_roles": ["senior software engineer", "systems"]},
        job=_job(),
    )
    assert result.score >= 70
    assert "C++" in result.matched_skills
    assert result.classification in {"excellent", "strong", "possible"}


def test_missing_skills_surface():
    result = compute_match(
        candidate_skills={"Python", "SQL"},
        candidate_titles=["Backend Engineer"],
        candidate_text="Python SQL backend APIs",
        candidate_location="Mumbai",
        preferences={"seniority": "MID"},
        job=_job(),
    )
    assert "C++" in result.missing_skills
    assert result.score < 90
