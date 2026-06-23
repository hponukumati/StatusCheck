from run import build_digest


class TestBuildDigest:
    def test_includes_only_nonempty_sections(self):
        digest = build_digest(added=["Acme"], interviewed=[], offered=[], rejected=["Globex"])
        assert "New applications (1):" in digest
        assert "  - Acme" in digest
        assert "Interviews" not in digest
        assert "Rejections (1):" in digest
        assert "  - Globex" in digest

    def test_empty_everything_returns_empty_string(self):
        assert build_digest([], [], [], []) == ""

    def test_lists_all_companies_in_a_section(self):
        digest = build_digest(added=["Acme", "Globex"], interviewed=[], offered=[], rejected=[])
        assert "  - Acme" in digest
        assert "  - Globex" in digest
