import unittest
from sun_valuation import dividend_prices, peg_prices
from tx_provisional import rotate_ohlc


class ValueAndGeometryTests(unittest.TestCase):
    def test_357(self):
        result = dividend_prices([5, 5, 5, 5, 5.05])
        self.assertEqual([round(x, 2) for x in result.values()], [71.57, 100.20, 167.00])

    def test_peg(self):
        result = peg_prices(21.37, 29.85)
        self.assertEqual([round(x) for x in result.values()], [478, 558, 638, 797, 957])

    def test_invalid_inputs(self):
        for data in ([1], [0]*5, [1, 1, 1, 1, float("nan")], [-1, 1, 1, 1, 1]):
            with self.assertRaises(ValueError):
                dividend_prices(data)
        with self.assertRaises(ValueError):
            peg_prices(1, 0)

    def test_rotation(self):
        source = [dict(open=101, high=104, low=100, close=103),
                  dict(open=103, high=105, low=102, close=104)]
        rotated = rotate_ohlc(source, 104)
        self.assertEqual(rotated, [dict(open=105, high=106, low=103, close=104),
                                   dict(open=107, high=108, low=104, close=105)])
        self.assertEqual(rotate_ohlc(rotated, 104), source)
