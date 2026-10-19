from offer import JobOffer


class SalaryParser:
    @staticmethod
    def extract_offer_text(
        text: str,
        offers: list[JobOffer],
    ) -> dict[int, str]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        positions: list[tuple[int, JobOffer]] = []
        search_from = 0

        for offer in offers:
            title = offer.title.strip().lower()

            for index in range(search_from, len(lines)):
                if title in lines[index].lower():
                    positions.append((index, offer))
                    search_from = index + 1
                    break

        result: dict[int, str] = {}

        for index, (start, offer) in enumerate(positions):
            end = positions[index + 1][0] if index + 1 < len(positions) else len(lines)

            result[id(offer)] = "\n".join(lines[start:end])

        return result
