from app.jobsources.base import RawJob
from app.utils.normalize import detect_remote_type, infer_seniority, normalize_title


def test_dedup_keys_stable():
    """Jobs from different sources with same URL should share identity signals."""
    a = RawJob(
        source="greenhouse",
        source_job_id="1",
        company="Acme",
        title="SDE II",
        location="Bangalore",
        application_url="https://example.com/jobs/1",
        description="C++ Linux",
    )
    b = RawJob(
        source="lever",
        source_job_id="xyz",
        company="Acme",
        title="Software Development Engineer II",
        location="Bangalore",
        application_url="https://example.com/jobs/1",
        description="C++ Linux",
    )
    assert a.application_url == b.application_url
    assert normalize_title(a.title) == normalize_title(b.title)
    assert infer_seniority(a.title) == infer_seniority(b.title)
    assert detect_remote_type(a.location) == detect_remote_type(b.location)
