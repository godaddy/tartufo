import unittest

from tartufo import tartufo


class EntropyTests(unittest.TestCase):

    def test_shannon(self):
        random_string_b64 = (
            "ZWVTjPQSdhwRgl204Hc51YCsritMIzn8B=/p9UyeX7xu6KkAGqfm3FJ+oObLDNEva"
        )
        random_string_hex = "b3A0a1FDfe86dcCE945B72"
        self.assertGreater(
            tartufo.shannon_entropy(random_string_b64, tartufo.BASE64_CHARS),
            4.5
        )
        self.assertGreater(
            tartufo.shannon_entropy(random_string_hex, tartufo.HEX_CHARS),
            3
        )


if __name__ == "__main__":
    unittest.main()
