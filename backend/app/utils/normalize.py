from __future__ import annotations

import re

# Technology alias normalization (Phase 3 building block, used in Phase 1 skill extraction)
TECH_ALIASES: dict[str, str] = {
    "c plus plus": "C++",
    "cplusplus": "C++",
    "cpp": "C++",
    "c/c++": "C++",
    "c++/c": "C++",
    "cxx": "C++",
    "python3": "Python",
    "python 3": "Python",
    "py": "Python",
    "linux os": "Linux",
    "gnu/linux": "Linux",
    "linuxptp": "LinuxPTP",
    "linux ptp": "LinuxPTP",
    "ptp": "PTP",
    "netconf": "NETCONF",
    "restconf": "RESTCONF",
    "multi-threading": "Multithreading",
    "multi threading": "Multithreading",
    "multithreading": "Multithreading",
    "device driver": "Device Drivers",
    "device drivers": "Device Drivers",
    "kernel": "Linux Kernel",
    "linux kernel": "Linux Kernel",
    "embedded c": "Embedded C",
    "sql": "SQL",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "mysql": "MySQL",
    "tcp/ip": "TCP/IP",
    "tcpip": "TCP/IP",
    "socket programming": "Sockets",
    "optical networking": "Optical Networking",
    "telecom": "Telecom",
    "telecommunications": "Telecom",
}

KNOWN_SKILLS = sorted(
    {
        "C",
        "C++",
        "Python",
        "Linux",
        "Multithreading",
        "System Programming",
        "Device Drivers",
        "Linux Kernel",
        "Networking",
        "Network Protocols",
        "NETCONF",
        "RESTCONF",
        "SQL",
        "PostgreSQL",
        "MySQL",
        "Embedded",
        "Embedded C",
        "Telecom",
        "Optical Networking",
        "PTP",
        "LinuxPTP",
        "TCP/IP",
        "Sockets",
        "Bash",
        "Git",
        "Docker",
        "Kubernetes",
        "Go",
        "Rust",
        "Java",
        "JavaScript",
        "TypeScript",
        "AWS",
        "Azure",
        "GCP",
        "Redis",
        "Kafka",
        "gRPC",
        "REST",
        "CI/CD",
        "Yocto",
        "RTOS",
        "FPGA",
        "Wireshark",
        "GDB",
        "Valgrind",
    },
    key=len,
    reverse=True,
)

SENIORITY_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(principal|distinguished|fellow)\b", re.I), "PRINCIPAL"),
    (re.compile(r"\b(staff|architect)\b", re.I), "STAFF"),
    (re.compile(r"\b(senior|sr\.?|lead|iii|3)\b", re.I), "SENIOR"),
    (re.compile(r"\b(mid|ii|2|sde\s*ii)\b", re.I), "MID"),
    (re.compile(r"\b(junior|jr\.?|intern|entry|i\b|1)\b", re.I), "JUNIOR"),
]

INDIA_LOCATIONS = {
    "india",
    "bangalore",
    "bengaluru",
    "hyderabad",
    "pune",
    "chennai",
    "noida",
    "gurgaon",
    "gurugram",
    "mumbai",
    "delhi",
    "new delhi",
    "kolkata",
    "ahmedabad",
    "jaipur",
    "kochi",
    "trivandrum",
    "thiruvananthapuram",
}


def normalize_skill(raw: str) -> str:
    cleaned = re.sub(r"\s+", " ", raw.strip())
    key = cleaned.lower()
    if key in TECH_ALIASES:
        return TECH_ALIASES[key]
    # Split C/C++
    if key in {"c/c++", "c++/c"}:
        return "C++"
    for known in KNOWN_SKILLS:
        if known.lower() == key:
            return known
    return cleaned


def expand_compound_skill(raw: str) -> list[str]:
    key = raw.strip().lower()
    if key in {"c/c++", "c++/c", "c & c++", "c and c++"}:
        return ["C", "C++"]
    return [normalize_skill(raw)]


def normalize_title(title: str) -> str:
    t = re.sub(r"\s+", " ", title.strip())
    t = re.sub(r"\bSDE\b", "Software Engineer", t, flags=re.I)
    t = re.sub(r"\bSoftware Development Engineer\b", "Software Engineer", t, flags=re.I)
    return t


def infer_seniority(title: str) -> str:
    for pattern, level in SENIORITY_PATTERNS:
        if pattern.search(title):
            return level
    return "MID"


def detect_remote_type(location: str | None, description: str | None = None) -> str:
    text = f"{location or ''} {description or ''}".lower()
    if re.search(r"\b(remote|work from home|wfh)\b", text):
        if re.search(r"\bhybrid\b", text):
            return "hybrid"
        return "remote"
    if re.search(r"\bhybrid\b", text):
        return "hybrid"
    if location:
        return "onsite"
    return "unknown"


def is_india_location(location: str | None) -> bool:
    if not location:
        return False
    loc = location.lower()
    return any(city in loc for city in INDIA_LOCATIONS)


def extract_skills_from_text(text: str) -> list[str]:
    found: list[str] = []
    lower = text.lower()
    for skill in KNOWN_SKILLS:
        # Word-boundary-ish match; allow C++ etc.
        pattern = re.escape(skill.lower())
        if re.search(rf"(?<![a-z0-9]){pattern}(?![a-z0-9])", lower):
            found.append(skill)
    # Special case: bare "C" language
    if re.search(r"(?<![a-z0-9])c(?![a-z0-9+#])", lower) and "C" not in found:
        # Avoid matching random single letters too aggressively — require nearby context
        if re.search(r"\b(c language|programming in c|c programming|proficient in c)\b", lower):
            found.append("C")
    return sorted(set(found), key=str.lower)
