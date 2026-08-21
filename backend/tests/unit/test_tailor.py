from app.services.resume.tailor import analyze_ats, tailor_resume_from_profile
from types import SimpleNamespace


def test_tailor_never_adds_unknown_skills():
    profile = SimpleNamespace(
        full_name="Rahul",
        email="r@example.com",
        phone=None,
        location="Bangalore",
        summary="Systems engineer.",
        skills=[
            SimpleNamespace(name="C++", normalized_name="C++", category="language", status="VERIFIED"),
            SimpleNamespace(name="Linux", normalized_name="Linux", category="os", status="VERIFIED"),
        ],
        experiences=[
            SimpleNamespace(
                title="Software Engineer",
                company="Acme",
                start_date="2020",
                end_date="Present",
                responsibilities=["Built C++ services on Linux", "Wrote docs"],
                technologies=["C++", "Linux"],
                status="VERIFIED",
            )
        ],
    )
    job = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000001",
        title="Senior C++ Engineer",
        company="NetCo",
        requirements=["C++", "Linux", "Rust"],
        description="Rust preferred",
    )
    content = tailor_resume_from_profile(profile, job)
    skill_names = {s["name"] for s in content["skills"]}
    assert "C++" in skill_names
    assert "Rust" not in skill_names  # must not invent


def test_ats_reports_gaps():
    job = SimpleNamespace(
        title="Engineer",
        requirements=["C++", "Linux", "Python"],
        description="",
    )
    result = analyze_ats("Experienced in C++ and Linux systems", job)
    assert "C++" in result["matched_keywords"]
    assert "Python" in result["missing_keywords"]
