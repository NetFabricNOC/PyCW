import unittest
import null_defs


class TestCompanyTypeFromId(TestCase):
    def test_company_type_from_id_default_success(self):
        self.assertEqual(null_defs.company_type_from_id("netfabric"), "Netfabric")

    def test_company_type_from_id_default_failed(self):
        self.assertEqual(null_defs.company_type_from_id("ampersand"), "Netfabric")

    def test_company_type_from_id_customer_success(self):
        self.assertEqual(null_defs.company_type_from_id("RACK59"), "Rack59")


class TestFixClosed(TestCase):
    def test_fix_closed_closed(self):
        self.assertEqual(null_defs.fix_closed(">Closed"), "Closed")

    def test_fix_closed_with_space(self):
        self.assertEqual(null_defs.fix_closed(">Closed "), "Closed")

    def test_fix_closed_random(self):
        self.assertEqual(null_defs.fix_closed("Random"), "Random")


class TestCloseTicket(TestCase):
    def test_close_ticket(self):
        self.fail()


class TestUpdateTicket(TestCase):
    def test_update_ticket(self):
        self.fail()


class TestCreateTicket(TestCase):
    def test_create_ticket(self):
        self.fail()


class TestSani(TestCase):
    def test_sani_slashes(self):
        self.assertEqual(null_defs.sani("test\\passed"), "testpassed")

if __name__ == "__main__":
    unittest.main()