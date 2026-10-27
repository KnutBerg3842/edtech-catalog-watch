from datetime import date

from price_watch import CourseOffer, assess_offer


def main() -> None:
    offer = CourseOffer(
        title="Practical Retrieval Systems",
        delivery="self-paced",
        learner_deadline=date(2026, 12, 15),
        review_threshold=80.0,
    )
    report = assess_offer(offer, observed_amount=72.0, today=date(2026, 10, 25))
    print(f"{report.title}: status={report.status}; reason={report.reason}")


if __name__ == "__main__":
    main()
