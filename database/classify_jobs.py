from modules.db_save import Database
from modules.job_classification_service import JobClassificationService
from modules.job_classifier import JobClassifier


def main():
    db = Database("new_offers.db")
    classifier = JobClassifier()
    classification_service = JobClassificationService(db, classifier, None)

    classification_service.process_jobs()


if __name__ == "__main__":
    main()
