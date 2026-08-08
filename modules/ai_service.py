import asyncio
import logging

from google import genai
from google.genai.errors import ClientError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from offer import CategoryValidationResponse, JobOffer, OffersResponse

logger = logging.getLogger(__name__)


# Function to parse job offers from text using the API
class AIService:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

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
        logger.debug("AI EXTRACT:", response.text)
        await asyncio.sleep(5)

        logger.debug("RAW RESPONSE: %s", response.text)

        if not response.parsed:
            logger.warning("Gemini returned no parsed response. Raw: %s", response.text)
            return []

        parsed_response = OffersResponse.model_validate(response.parsed)

        if not parsed_response.offers:
            logger.info("No job offers found")

        return parsed_response.offers

    async def validate_category_api(self, clean_title: str, categories: list[str]) -> CategoryValidationResponse:
        """Validate/classify a job title into a category using the AI API.

        Return a CategoryValidationResponse.
        """
        categories_str = ", ".join(categories)
        prompt = (
            f"Classify the job title. Available categories: {categories_str}. "
            f'Return the correct category or unknown:\n"{clean_title}"'
        )

        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model="models/gemini-3.1-flash-lite",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": CategoryValidationResponse.model_json_schema(),
                "temperature": 0.0,
            },
        )

        logger.info("CATEGORY RAW RESPONSE: %s", response.text)

        if not response.parsed:
            logger.warning("Gemini returned no parsed response for category validation. Raw: %s", response.text)
            return CategoryValidationResponse(category="unknown")

        parsed = CategoryValidationResponse.model_validate(response.parsed)

        return parsed
