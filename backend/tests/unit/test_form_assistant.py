from app.services.applications.form_assistant import FieldConfidence, classify_field, map_profile_to_fields


def test_sensitive_fields_are_red():
    assert classify_field("Disability status") == FieldConfidence.RED
    assert classify_field("Veteran status") == FieldConfidence.RED
    assert classify_field("Salary expectations") == FieldConfidence.RED
    assert classify_field("CAPTCHA") == FieldConfidence.RED


def test_safe_fields_are_green():
    assert classify_field("Email address") == FieldConfidence.GREEN
    assert classify_field("Phone number") == FieldConfidence.GREEN


def test_map_profile_does_not_fill_red_fields():
    fields = map_profile_to_fields(
        {"email": "a@b.com", "full_name": "Ada", "phone": "123"},
        ["Email", "Disability accommodation", "Why do you want this role?"],
    )
    by_label = {f.label: f for f in fields}
    assert by_label["Email"].value == "a@b.com"
    assert by_label["Disability accommodation"].value is None
    assert by_label["Disability accommodation"].confidence == FieldConfidence.RED
