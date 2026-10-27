from datetime import date

from src.price_watch import CourseOffer, assess_offer


def test_threshold_and_deadline_produce_review_report() -> None:
    offer = CourseOffer("RAG Foundations", "cohort", date(2026, 11, 30), 100.0)

    report = assess_offer(offer, observed_amount=95.0, today=date(2026, 10, 25))

    assert report.status == "review"
    assert report.reason == "amount is within educator threshold"


def test_passed_deadline_holds_even_when_amount_is_low() -> None:
    offer = CourseOffer("Agent Evaluation", "live", date(2026, 10, 1), 100.0)

    report = assess_offer(offer, observed_amount=50.0, today=date(2026, 10, 25))

    assert report.status == "hold"
    assert report.reason == "learner deadline passed"
