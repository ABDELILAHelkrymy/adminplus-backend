from unittest import TestCase

from .gpt_invoice_parser import GPTInvoiceParser


class GPTInvoiceParserTest(TestCase):
    def test_normalizes_iso_datetimes_to_dates(self):
        data = GPTInvoiceParser.__new__(GPTInvoiceParser)._post_process(
            {
                "date": "2025-03-19T00:00:00Z",
                "due_date": "2025-04-19T00:00:00+00:00",
                "paid_date": None,
            }
        )

        self.assertEqual(data["date"], "2025-03-19")
        self.assertEqual(data["due_date"], "2025-04-19")
        self.assertIsNone(data["paid_date"])
