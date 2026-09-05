import asyncio
import logging
import time

from google import genai
from google.genai.errors import ServerError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from offer import CategoryValidationResponse, JobContract, JobContractResponse, JobOffer, OffersResponse

logger = logging.getLogger(__name__)


# Function to parse job offers from text using the API
class AIService:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self._api_lock = asyncio.Lock()
        self._last_api_call = 0.0
        self._api_delay = 4.0

    async def _wait_before_api_call(self):
        async with self._api_lock:
            now = time.monotonic()
            elapsed = now - self._last_api_call

            if elapsed < self._api_delay:
                await asyncio.sleep(self._api_delay - elapsed)

            self._last_api_call = time.monotonic()

    @retry(
        retry=retry_if_exception_type(ServerError),
        wait=wait_exponential(multiplier=1, min=4, max=60),  # Wait: 4s, 8s, 16s...
        stop=stop_after_attempt(5),
    )
    async def parser_offers_api(self, text: str) -> list[JobOffer]:
        prompt = (
            "Extract all job offers from this email text. "
            "Return each job offer separately. "
            "Do not extract salary or contract information.\n\n"
            'VAT: true if "VAT" is explicitly stated, otherwise null.'
            f'"{text}"'
        )
        await self._wait_before_api_call()

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

        logger.debug(f"AI OFFERS RAW RESPONSE: {response.text}")

        if not response.parsed:
            logger.warning(f"Gemini returned no parsed response. Raw: {response.text}")
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
        await self._wait_before_api_call()
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

        logger.info(f"CATEGORY RAW RESPONSE: {response.text}")

        if not response.parsed:
            logger.warning(f"Gemini returned no parsed response for category validation. Raw: {response.text}")
            return CategoryValidationResponse(category="unknown")

        parsed = CategoryValidationResponse.model_validate(response.parsed)

        return parsed

    @retry(
        retry=retry_if_exception_type(ServerError),
        wait=wait_exponential(multiplier=1, min=4, max=60),  # Wait: 4s, 8s, 16s...
        stop=stop_after_attempt(5),
    )
    async def validate_salary_api(
        self,
        salary_text: str,
    ) -> list[JobContract]:

        prompt = (
            "Extract salary and contract information ONLY from the provided job offer text.\n"
            "Do not infer, estimate, copy, or use information from other offers.\n"
            "If salary or contract information is not explicitly present, return an empty contracts list.\n"
            "Return only contracts explicitly mentioned in this offer.\n\n"
            f"JOB OFFER:\n{salary_text}"
        )
        await self._wait_before_api_call()
        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model="models/gemini-3.1-flash-lite",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": JobContractResponse.model_json_schema(),
                "temperature": 0.0,
            },
        )

        logger.debug(f"SALARY RAW RESPONSE: {response.text}")

        if not response.parsed:
            logger.warning(f"Gemini returned no parsed response for salary extraction. Raw: {response.text}")
            return []

        parsed_response = JobContractResponse.model_validate(response.parsed)

        if not parsed_response.contracts:
            logger.info("No salary contracts found")
            return []

        contracts = [
            contract
            for contract in parsed_response.contracts
            if (
                contract.contract_type is not None
                or contract.salary_min_offer is not None
                or contract.salary_max_offer is not None
            )
        ]

        return contracts
