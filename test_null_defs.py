import null_defs

class TestSani:
    def test_removes_slashes:
        assert null_defs.sani("test\passed") == "testpassed"
    def test_removes_quotes:
        assert null_defs.sani('test"passed') == "testpassed"
    def test_removes_both:
        assert null_defs.sani("""This string has no " or \'s""") == "This string has no  or 's"
    def test_sanitizes_test_payload:
        assert null_defs.sani() == ""
