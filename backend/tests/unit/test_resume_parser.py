"""Unit tests for resume parsing — never invent facts."""

from app.models.candidate import FactStatus
from app.services.resume.parser import parse_resume_text


SAMPLE_RESUME = """
Rahul Sharma
Bangalore, India
rahul.sharma@example.com
+91 98765 43210

Summary
Senior Software Engineer with 6 years of experience in C++, Linux systems programming,
networking protocols, and embedded software development.

Skills
C, C++, Python, Linux, Multithreading, Device Drivers, NETCONF, SQL, PTP, LinuxPTP,
TCP/IP, Optical Networking, Git, GDB

Experience
Senior Software Engineer at Acme Networks
Jan 2020 - Present
- Developed NETCONF-based configuration management for optical transport systems
- Implemented LinuxPTP synchronization for carrier-grade networking gear
- Built multithreaded C++ services for device driver control planes

Software Engineer at SysSoft Pvt Ltd
Jun 2017 - Dec 2019
- Wrote Linux character device drivers in C for custom PCI hardware
- Optimized socket networking stack performance under high load

Projects
Optical Control Plane
Built a prototype NETCONF/YANG management agent for OTN switches using C++ and Python.

Education
Indian Institute of Technology
B.Tech Computer Science
"""


def test_parse_extracts_contact_and_skills():
    result = parse_resume_text(SAMPLE_RESUME)
    assert result.candidate["name"]["value"] == "Rahul Sharma"
    assert result.candidate["name"]["status"] == FactStatus.VERIFIED.value
    assert result.candidate["email"]["value"] == "rahul.sharma@example.com"
    assert result.candidate["phone"]["status"] == FactStatus.VERIFIED.value
    assert result.candidate["location"]["value"] == "Bangalore"

    skill_names = {s["name"] for s in result.skills}
    assert "C++" in skill_names
    assert "Python" in skill_names
    assert "Linux" in skill_names
    assert "NETCONF" in skill_names
    assert "LinuxPTP" in skill_names
    assert all(s["status"] == FactStatus.VERIFIED.value for s in result.skills)


def test_parse_does_not_invent_employer():
    result = parse_resume_text(SAMPLE_RESUME)
    companies = {e.get("company") for e in result.experience}
    assert "Acme Networks" in companies or any("Acme" in (c or "") for c in companies)
    # Must not invent employers not in text
    assert "Google" not in companies
    assert "Meta" not in companies


def test_parse_marks_missing_fields():
    sparse = "Only a name\nJane Doe\n"
    result = parse_resume_text(sparse)
    assert "email" in result.missing_fields
    assert result.candidate["email"]["status"] == FactStatus.MISSING.value


def test_parse_expands_cpp_aliases_from_skills_section():
    text = """
Alex
alex@test.com

Skills
Cpp, Linux OS, multi-threading
"""
    result = parse_resume_text(text)
    names = {s["name"] for s in result.skills}
    assert "C++" in names
    assert "Linux" in names
    assert "Multithreading" in names
