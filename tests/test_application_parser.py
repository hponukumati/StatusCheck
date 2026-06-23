from application_parser import (
    extract_company_from_sender,
    extract_company_from_subject,
    extract_position_from_subject,
    parse_application_email,
)


class TestExtractCompanyFromSubject:
    def test_thank_you_for_applying_to(self):
        assert extract_company_from_subject("Thank you for applying to Acme Corp") == "Acme Corp"

    def test_thank_you_for_applying_at(self):
        assert extract_company_from_subject("Thank you for applying at Globex") == "Globex"

    def test_we_received_your_application_for(self):
        assert extract_company_from_subject("We received your application for Initech") == "Initech"

    def test_application_received_with_colon(self):
        assert extract_company_from_subject("Application received: Hooli") == "Hooli"

    def test_dash_separated_company_first(self):
        assert extract_company_from_subject("Acme - Application received") == "Acme"

    def test_role_at_company(self):
        result = extract_company_from_subject("Software Engineer at Stark Industries")
        assert result == "Stark Industries"

    def test_empty_subject_returns_none(self):
        assert extract_company_from_subject("") is None

    def test_none_subject_returns_none(self):
        assert extract_company_from_subject(None) is None

    def test_whitespace_only_subject_returns_none(self):
        assert extract_company_from_subject("   ") is None

    def test_prefix_with_role_then_dash_company(self):
        result = extract_company_from_subject("Thank you for applying to Software Engineer - Wayne Enterprises")
        assert result == "Software Engineer"


class TestExtractPositionFromSubject:
    def test_role_at_company_extracts_role(self):
        result = extract_position_from_subject("Application received - Software Engineer at Acme")
        assert result == "Software Engineer"

    def test_no_role_pattern_returns_empty(self):
        assert extract_position_from_subject("Thank you for applying to Acme Corp") == ""

    def test_empty_subject_returns_empty(self):
        assert extract_position_from_subject("") == ""

    def test_none_subject_returns_empty(self):
        assert extract_position_from_subject(None) == ""


class TestExtractCompanyFromSender:
    def test_display_name_preferred(self):
        result = extract_company_from_sender("Acme Recruiting <noreply@acme.com>")
        assert result == "Acme Recruiting"

    def test_falls_back_to_domain_when_no_display_name(self):
        result = extract_company_from_sender("noreply@globex.com")
        assert result == "Globex"

    def test_domain_strips_common_tld(self):
        result = extract_company_from_sender("careers@initech.io")
        assert result == "Initech"

    def test_empty_sender_returns_none(self):
        assert extract_company_from_sender("") is None

    def test_none_sender_returns_none(self):
        assert extract_company_from_sender(None) is None

    def test_quoted_display_name(self):
        result = extract_company_from_sender('"Hooli Talent Team" <talent@hooli.com>')
        assert result == "Hooli Talent Team"


class TestParseApplicationEmail:
    def test_uses_subject_company_when_available(self):
        company, position, confidence = parse_application_email(
            "Thank you for applying to Acme Corp", "noreply@acme.com"
        )
        assert company == "Acme Corp"
        assert confidence == "high"

    def test_falls_back_to_sender_when_subject_has_no_company(self):
        company, position, confidence = parse_application_email("", "noreply@globex.com")
        assert company == "Globex"
        assert confidence == "low"

    def test_falls_back_to_unknown_when_nothing_works(self):
        company, position, confidence = parse_application_email("", "")
        assert company == "Unknown"
        assert confidence == "low"

    def test_extracts_position_alongside_company(self):
        company, position, confidence = parse_application_email(
            "Application received - Software Engineer at Acme", "noreply@acme.com"
        )
        assert position == "Software Engineer"

    def test_company_before_status_phrase_is_high_confidence(self):
        company, position, confidence = parse_application_email(
            "Acme - Application received", "noreply@acme.com"
        )
        assert company == "Acme"
        assert confidence == "high"

    def test_role_at_company_is_high_confidence(self):
        company, position, confidence = parse_application_email(
            "Software Engineer at Stark Industries", "noreply@stark.com"
        )
        assert company == "Stark Industries"
        assert confidence == "high"

    def test_generic_colon_split_is_low_confidence(self):
        # Ambiguous subject with no recognizable keyword on either side of the colon
        company, position, confidence = parse_application_email(
            "Update: Wayne Enterprises", "noreply@wayne.com"
        )
        assert company == "Wayne Enterprises"
        assert confidence == "low"
