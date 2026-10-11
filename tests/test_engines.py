import unittest

from engines import manager as M
from engines.gtp import gtp_to_xy, xy_to_gtp
from engines.piskvork import PiskvorkEngine
from engines.uci import move_to_uci, uci_to_move


class CoordinateTest(unittest.TestCase):
    def test_gtp_roundtrip(self):
        for x in range(19):
            for y in range(19):
                self.assertEqual(gtp_to_xy(xy_to_gtp(x, y, 19), 19), (x, y))

    def test_gtp_pass(self):
        self.assertIsNone(gtp_to_xy("PASS", 19))
        self.assertIsNone(gtp_to_xy("", 19))

    def test_uci_roundtrip(self):
        for fx in range(9):
            for fy in range(10):
                for tx in range(9):
                    for ty in range(10):
                        mv = ((fx, fy), (tx, ty))
                        self.assertEqual(uci_to_move(move_to_uci(mv)), mv)

    def test_uci_known_encoding(self):
        # 红兵从 (0,6) 走到 (0,5)：ICCS 记作 a3a4
        self.assertEqual(move_to_uci(((0, 6), (0, 5))), "a3a4")
        self.assertEqual(uci_to_move("a3a4"), ((0, 6), (0, 5)))

    def test_piskvork_mapping_is_involution(self):
        eng = PiskvorkEngine("nonexistent.exe", size=15)
        for y in range(15):
            self.assertEqual(eng._map(*eng._map(3, y)), (3, y))


class EnginePathTest(unittest.TestCase):
    def test_paths_point_at_windows_binaries(self):
        self.assertTrue(str(M.KATAGO).endswith("katago.exe"))
        self.assertTrue(str(M.PIKAFISH).endswith(".exe"))
        self.assertTrue(str(M.RAPFI).endswith(".exe"))


if __name__ == "__main__":
    unittest.main()
