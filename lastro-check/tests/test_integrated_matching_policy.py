from datetime import date
import unittest

from lastro.reconciliation.matching_policy import MatchEvent, MatchMethod, MatchPolicy, MatchStatus, decide_match


def e(event_id: str, day: int, ref: str | None = None, strong: bool = True) -> MatchEvent:
    return MatchEvent(event_id, date(2026, 9, day), ref, strong)


class MatchingPolicyTests(unittest.TestCase):
    def test_exact_reference_has_precedence_over_heuristics(self):
        decision = decide_match(
            e("target", 10, "REF-1"),
            [e("near", 10, "OTHER"), e("exact", 25, "REF-1")],
            MatchPolicy(True, 2),
        )
        self.assertEqual((decision.status, decision.method, decision.matched_event_id), (MatchStatus.MATCHED, MatchMethod.EXACT_REFERENCE, "exact"))

    def test_duplicate_exact_reference_is_ambiguous(self):
        decision = decide_match(e("target", 10, "REF-1"), [e("a", 10, "REF-1"), e("b", 11, "REF-1")], MatchPolicy(True, 2))
        self.assertEqual(decision.status, MatchStatus.AMBIGUOUS)
        self.assertEqual(decision.method, MatchMethod.EXACT_REFERENCE)

    def test_outside_window_never_becomes_heuristic_match(self):
        decision = decide_match(e("target", 1), [e("far", 28)], MatchPolicy(True, 3))
        self.assertEqual(decision.status, MatchStatus.UNMATCHED)

    def test_multiple_inside_window_are_ambiguous(self):
        decision = decide_match(e("target", 10), [e("a", 9), e("b", 11)], MatchPolicy(True, 3))
        self.assertEqual(decision.status, MatchStatus.AMBIGUOUS)
        self.assertEqual(decision.method, MatchMethod.BOUNDED_HEURISTIC)

    def test_no_bound_means_no_heuristic_match(self):
        decision = decide_match(e("target", 10), [e("a", 10)], MatchPolicy(True, None))
        self.assertEqual((decision.status, decision.method), (MatchStatus.UNMATCHED, MatchMethod.NONE))

    def test_synthetic_or_unasserted_reference_cannot_be_exact(self):
        target = MatchEvent("target", date(2026, 9, 10), "generated")
        candidate = MatchEvent("candidate", date(2026, 9, 10), "generated")
        decision = decide_match(target, [candidate], MatchPolicy(False, 0))
        self.assertEqual((decision.status, decision.method), (MatchStatus.UNMATCHED, MatchMethod.NONE))

    def test_decision_is_deterministic(self):
        target = e("target", 10)
        policy = MatchPolicy(True, 5)
        self.assertEqual(decide_match(target, [e("z", 12), e("a", 9)], policy), decide_match(target, [e("a", 9), e("z", 12)], policy))

    def test_window_rejects_float_and_bool(self):
        for value in (1.5, True):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    MatchPolicy(True, value)


if __name__ == "__main__":
    unittest.main()
