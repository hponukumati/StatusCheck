from csv_store import (
    add_application,
    get_rows_with_status,
    load_rows,
    update_status,
)


def _add(csv_path, company, email_id):
    add_application(
        csv_path,
        company_name=company,
        applied_date="2026-01-01",
        application_email_id=email_id,
        subject=f"Application received: {company}",
        sender_email="noreply@example.com",
        position="Engineer",
        confidence="high",
    )


class TestGetRowsWithStatus:
    def test_returns_only_matching_statuses(self, tmp_path):
        csv_path = tmp_path / "applications.csv"
        _add(csv_path, "Acme", "1")
        _add(csv_path, "Globex", "2")
        update_status(csv_path, "Globex", "Interview", ["Applied"])

        applied = get_rows_with_status(csv_path, ["Applied"])
        interview = get_rows_with_status(csv_path, ["Interview"])

        assert [r["company_name"] for r in applied] == ["Acme"]
        assert [r["company_name"] for r in interview] == ["Globex"]

    def test_accepts_multiple_statuses(self, tmp_path):
        csv_path = tmp_path / "applications.csv"
        _add(csv_path, "Acme", "1")
        _add(csv_path, "Globex", "2")
        update_status(csv_path, "Globex", "Offer", ["Applied"])

        rows = get_rows_with_status(csv_path, ["Applied", "Offer"])
        assert {r["company_name"] for r in rows} == {"Acme", "Globex"}


class TestUpdateStatus:
    def test_updates_matching_company_and_status(self, tmp_path):
        csv_path = tmp_path / "applications.csv"
        _add(csv_path, "Acme", "1")

        updated = update_status(csv_path, "Acme", "Interview", ["Applied"])

        assert updated == 1
        rows = load_rows(csv_path)
        assert rows[0]["status"] == "Interview"

    def test_does_not_update_company_in_wrong_status(self, tmp_path):
        csv_path = tmp_path / "applications.csv"
        _add(csv_path, "Acme", "1")
        update_status(csv_path, "Acme", "Rejected", ["Applied"])

        # Already Rejected - an Interview update should not touch it
        updated = update_status(csv_path, "Acme", "Interview", ["Applied"])

        assert updated == 0
        rows = load_rows(csv_path)
        assert rows[0]["status"] == "Rejected"

    def test_rejection_can_override_offer(self, tmp_path):
        csv_path = tmp_path / "applications.csv"
        _add(csv_path, "Acme", "1")
        update_status(csv_path, "Acme", "Offer", ["Applied"])

        updated = update_status(csv_path, "Acme", "Rejected", ["Applied", "Interview", "Offer"])

        assert updated == 1
        rows = load_rows(csv_path)
        assert rows[0]["status"] == "Rejected"

    def test_no_matching_company_returns_zero(self, tmp_path):
        csv_path = tmp_path / "applications.csv"
        _add(csv_path, "Acme", "1")

        updated = update_status(csv_path, "Nonexistent", "Interview", ["Applied"])

        assert updated == 0
