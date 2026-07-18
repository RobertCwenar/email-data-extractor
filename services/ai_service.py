import asyncio
import logging

from google import genai
from google.genai.errors import ClientError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from offer import JobOffer, OffersResponse


# Function to parse job offers from text using the API
class AIService:
    def __init__(self, api_key: str, logger=None):
        self.client = genai.Client(api_key=api_key)
        self.logger = logger or logging.getLogger(__name__)

    @retry(
        retry=retry_if_exception_type(ClientError),
        wait=wait_exponential(multiplier=1, min=4, max=60),  # Czekaj: 4s, 8s, 16s...
        stop=stop_after_attempt(5),
    )
    async def parser_offers_api(self, text: str) -> list[JobOffer]:
        prompt = f'Extract all job offers from this text mail. If salary is missing, set salary to null:\n"{text}"'

        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model="models/gemini-3.1-flash-lite",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": OffersResponse.model_json_schema(),
                "temperature": 0.0,
            },
        )
        print("AI EXTRACT:", response.text)
        await asyncio.sleep(5)

        self.logger.debug("RAW RESPONSE: %s", response.text)

        if not response.parsed:
            self.logger.warning("Gemini returned no parsed response. Raw: %s", response.text)
            return []

        parsed_response = OffersResponse.model_validate(response.parsed)

        print("PARSED:", len(parsed_response.offers), [o.title for o in parsed_response.offers])

        if not parsed_response.offers:
            self.logger.info("No job offers found")

        return parsed_response.offers
