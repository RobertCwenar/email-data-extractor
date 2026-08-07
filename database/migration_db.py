import sqlite3

DB = "new_offers.db"


def migrate_job_details():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title
        FROM Offers
    """)

    offers = cursor.fetchall()

    print(f"Found {len(offers)} offers")

    for offer in offers:
        cursor.execute(
            """
            INSERT INTO JobDetails
            (offer_id, clean_title, level, category)
            VALUES (?, ?, ?, ?)
            """,
            (
                offer[0],
                offer[1],
                None,
                None,
            ),
        )

    conn.commit()

    cursor.execute("""
        SELECT COUNT(*)
        FROM JobDetails
    """)

    print("JobDetails after:", cursor.fetchone()[0])

    conn.close()


if __name__ == "__main__":
    migrate_job_details()
