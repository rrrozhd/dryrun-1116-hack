"""Agent planning with a stub decider: which questions get asked and how answers are keyed."""

import unittest

from datarescue.agent import plan

FIELDS = {
    "status": {"type": "enum", "description": "order status", "values": ["open", "shipped"]},
    "email": {"type": "string", "description": "customer email"},
}


class PlanTest(unittest.TestCase):
    def setUp(self):
        self.asked = []

    def decide(self, desc, allowed, raw):
        self.asked.append(raw)
        table = {"Order Status": "status", "dispatched": "shipped"}
        value = table.get(raw)
        return {"value": value, "score": 0.9 if value else 0.1, "decided_by": "stub", "reason": "stub"}

    def test_maps_headers_then_distinct_enum_values(self):
        profile = {"columns": [
            {"index": 0, "header": "Order Status", "values": {"open": 2, "dispatched": 1, "lost": 1, "": 3}},
            {"index": 1, "header": "email", "values": {"a@x": 1}},
            {"index": 2, "header": "memo", "values": {"hi": 1}},
        ]}
        header_map, value_maps = plan(profile, FIELDS, self.decide)
        self.assertEqual(header_map[0]["value"], "status")
        self.assertEqual(header_map[1]["decided_by"], "exact")  # exact header skips the decider
        self.assertIsNone(header_map[2]["value"])  # unmatched header: no value mapping
        self.assertEqual(set(value_maps), {0})  # only the resolved enum column
        self.assertEqual(value_maps[0]["dispatched"]["value"], "shipped")
        self.assertEqual(value_maps[0]["open"]["decided_by"], "exact")
        self.assertIsNone(value_maps[0]["lost"]["value"])
        self.assertNotIn("", value_maps[0])  # empty cells are never mapped
        self.assertNotIn("open", self.asked)
        self.assertNotIn("email", self.asked)


if __name__ == "__main__":
    unittest.main()
