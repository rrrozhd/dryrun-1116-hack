"""End-to-end path with a stub decider: failed headers preserve values, collisions abstain, scoring."""

import json
import tempfile
import unittest
from pathlib import Path

from datarescue import agent
from datarescue.e2e import read_rows, score

SCHEMA = {"fields": {"status": {"type": "enum", "description": "order status", "values": ["open", "shipped"]},
                     "email": {"type": "string", "description": "email"}}}
CSV = "Order Status,Mail\nopen,a@x\ndispatched,b@x\nlost,c@x\n"


def stub(table):
    def decide(desc, allowed, raw):
        v = table.get(raw)
        return {"value": v, "score": 0.9 if v else 0.0, "decided_by": "stub", "reason": "stub"}
    return decide


class E2ETest(unittest.TestCase):
    def run_agent(self, table):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "in.csv").write_text(CSV, encoding="utf-8")
        (tmp / "schema.json").write_text(json.dumps(SCHEMA), encoding="utf-8")
        agent.run(tmp / "in.csv", tmp / "schema.json", tmp / "out", stub(table))
        return read_rows(tmp / "in.csv"), read_rows(tmp / "out" / "cleaned.csv")

    def test_failed_header_preserves_values(self):
        src, out = self.run_agent({"dispatched": "shipped"})  # header unresolved
        self.assertEqual(out, src)

    def test_collision_abstains_and_preserves_values(self):
        src, out = self.run_agent({"Order Status": "status", "Mail": "status", "dispatched": "shipped"})
        self.assertEqual(out, src)

    def test_resolved_header_maps_values_and_keeps_shape(self):
        src, out = self.run_agent({"Order Status": "status", "Mail": "email", "dispatched": "shipped"})
        self.assertEqual(out[0], ["status", "email"])
        self.assertEqual([r[0] for r in out[1:]], ["open", "shipped", "lost"])
        self.assertEqual((len(out), len(out[0])), (len(src), len(src[0])))

    def test_score_counts_per_cell_and_unlabelled_must_stay(self):
        gold = {"headers": {"Order Status": "status", "Mail": "email"},
                "values": {"status": {"dispatched": "shipped", "lost": None}}}
        src = [["Order Status", "Mail"], ["open", "a@x"], ["dispatched", "b@x"], ["lost", "c@x"]]
        out = [["status", "Mail"], ["opened", "a@x"], ["shipped", "b@x"], ["lost", "c@x"]]
        s = score(src, out, gold)
        self.assertEqual((s["header"]["correct_change"], s["header"]["missed"]), (1, 1))
        self.assertEqual(s["cell"]["correct_change"], 1)  # dispatched -> shipped
        self.assertEqual(s["cell"]["wrong_change"], 1)  # unlabelled 'open' must stay unchanged
        self.assertEqual(s["cell"]["correct_abstain"], 1)  # lost: gold says abstain
        with self.assertRaises(ValueError):
            score(src, out[:-1], gold)


if __name__ == "__main__":
    unittest.main()
