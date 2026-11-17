"""Decision logic of the model decider, with a stub in place of the model."""

import unittest

from datarescue.model import decide_with


def stub(table):
    """probs_fn that gives each option a fixed weight regardless of its position."""
    def probs_fn(field_desc, raw, options):
        weights = [table.get("<none>", 0.0)] + [table.get(o, 0.0) for o in options]
        total = sum(weights) or 1.0
        return [w / total for w in weights]
    return probs_fn


class DecideTest(unittest.TestCase):
    def test_picks_confident_option(self):
        d = decide_with(stub({"CA": 0.9, "CO": 0.1}), "state", ["CA", "CO", "CT"], "Calif.", threshold=0.5)
        self.assertEqual(d["value"], "CA")
        self.assertEqual(d["decided_by"], "model")
        self.assertAlmostEqual(d["score"], 0.9)

    def test_abstains_below_threshold(self):
        d = decide_with(stub({"CA": 0.4, "CO": 0.35, "CT": 0.25}), "state", ["CA", "CO", "CT"], "C", threshold=0.5)
        self.assertIsNone(d["value"])
        self.assertIn("abstain", d["reason"])

    def test_abstains_when_none_beats_best(self):
        d = decide_with(stub({"<none>": 0.6, "GA": 0.4}), "state", ["GA"], "Georgia", threshold=0.3)
        self.assertIsNone(d["value"])

    def test_position_bias_cancels_over_two_orders(self):
        def first_wins(field_desc, raw, options):  # always prefers whatever is listed first
            return [0.0, 0.6] + [0.4 / (len(options) - 1)] * (len(options) - 1)
        d = decide_with(first_wins, "state", ["NJ", "NY"], "N. York", threshold=0.55, orders=2)
        self.assertIsNone(d["value"])  # 0.5 each after averaging: no confident pick
        d1 = decide_with(first_wins, "state", ["NJ", "NY"], "N. York", threshold=0.55, orders=1)
        self.assertEqual(d1["value"], "NJ")  # one order shows the bias the second order removes

    def test_empty_allowed_abstains(self):
        self.assertIsNone(decide_with(stub({}), "state", [], "x")["value"])


class LargeEnumTest(unittest.TestCase):
    def test_more_than_nine_options_go_in_rounds(self):
        states = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "MA", "NY"]
        seen = []
        def probs_fn(field_desc, raw, options):
            seen.append(len(options))
            return stub({"MA": 0.9, "AL": 0.05})(field_desc, raw, options)
        d = decide_with(probs_fn, "state", states, "Mass", threshold=0.5, orders=1)
        self.assertEqual(d["value"], "MA")
        self.assertTrue(all(n <= 9 for n in seen))


class CascadeTest(unittest.TestCase):
    """Module-level decide: baseline first, model only where the baseline abstains."""

    def setUp(self):
        import datarescue.model as m
        self.m, self.saved, self.calls = m, m._decider, []
        test = self

        class Stub:
            def decide(self, field_desc, allowed, raw):
                test.calls.append(raw)
                return {"value": "shipped", "score": 0.8, "decided_by": "model", "reason": "stub"}
        setattr(m, "_decider", Stub())

    def tearDown(self):
        setattr(self.m, "_decider", self.saved)

    def test_baseline_match_skips_model(self):
        d = self.m.decide("status", ["open", "shipped"], "Shipped ")
        self.assertEqual((d["value"], d["decided_by"]), ("shipped", "baseline"))
        self.assertEqual(self.calls, [])

    def test_model_answers_where_baseline_abstains(self):
        d = self.m.decide("status", ["open", "shipped"], "dispatched")
        self.assertEqual((d["value"], d["decided_by"]), ("shipped", "model"))
        self.assertEqual(self.calls, ["dispatched"])


if __name__ == "__main__":
    unittest.main()
