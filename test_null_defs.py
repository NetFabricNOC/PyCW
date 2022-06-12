import null_defs

class TestSani:
    def test_removes_slashes(self):
        assert null_defs.sani("test\\passed") == "testpassed"

    def test_removes_quotes(self):
        assert null_defs.sani('test"passed') == "testpassed"

    def test_removes_both(self):
        assert null_defs.sani("""This string has no " or \\'s""") == "This string has no  or 's"

    def test_sanitizes_test_payload(self):
        assert null_defs.sani() == ""


# TODO: test ticket creation with unexpected proxies, should fail to the default.

