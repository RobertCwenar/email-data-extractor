import asyncio
import logging
import time

from google import genai
from google.genai.errors import ClientError, ServerError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from config import config
from offer import CategoryValidationResponse, JobContract, JobContractResponse, JobOffer, OffersResponse

logger = logging.getLogger(__name__)


RETRY_MULTIPLIER = 1
RETRY_MIN_WAIT = 6
RETRY_MAX_WAIT = 60
RETRY_ATTEMPTS = 10
API_DELAY = 5.0


# Function to parse job offers from text using the API
class AIService:
    def __init__(self, api_key: str) -> None:
        self.client = genai.Client(api_key=api_key)
        self._api_lock = asyncio.Lock()
        self._last_api_call = 0.0
        self._api_delay = API_DELAY
        self._models = config.get_list(["ai_models"])

    async def _wait_before_api_call(self) -> None:
        async with self._api_lock:
            now = time.monotonic()
            elapsed = now - self._last_api_call

            if elapsed < self._api_delay:
                await asyncio.sleep(self._api_delay - elapsed)

            self._last_api_call = time.monotonic()

    async def _generate_response(
        self,
        prompt: str,
        response_schema: dict,
    ):
        last_error = None

        for model in self._models:
            try:
                await self._wait_before_api_call()

                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=model,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": response_schema,
                        "temperature": 0.0,
                    },
                )

                logger.info("AI request successful with model: %s", model)

                return response

            except (ServerError, ClientError) as error:
                last_error = error

                logger.warning("AI request failed with model %s: %s", model, error)

        if last_error is not None:
            raise last_error

        raise RuntimeError("No AI models configured")

    @retry(
        retry=retry_if_exception_type(ServerError),
        wait=wait_exponential(multiplier=RETRY_MULTIPLIER, min=RETRY_MIN_WAIT, max=RETRY_MAX_WAIT),
        stop=stop_after_attempt(RETRY_ATTEMPTS),
    )
    async def parser_offers_api(self, text: str) -> list[JobOffer]:
        prompt = (
            "Extract all job offers from this email text. "
            "Return each job offer separately. "
            "Do not extract salary or contract information.\n\n"
            'VAT: true if "VAT" is explicitly stated, otherwise null.'
            f'"{text}"'
        )

        response = await self._generate_response(prompt, OffersResponse.model_json_schema())

        logger.debug(f"AI OFFERS RAW RESPONSE: {response.text}")

        if not response.parsed:
            logger.warning(f"Gemini returned no parsed response. Raw: {response.text}")
            return []

        parsed_response = OffersResponse.model_validate(response.parsed)

        if not parsed_response.offers:
            logger.debug("No job offers found")

        return parsed_response.offers

    async def validate_category_api(
        self,
        clean_title: str,
        categories: list[str],
    ) -> CategoryValidationResponse:
        """Validate/classify a job title into a category using the AI API.

        Return a CategoryValidationResponse.
        """
        categories_str = ", ".join(categories)
        prompt = (
            f"Classify the job title. Available categories: {categories_str}. "
            f'Return the correct category or unknown:\n"{clean_title}"'
        )

        response = await self._generate_response(prompt, CategoryValidationResponse.model_json_schema())

        logger.debug(f"CATEGORY RAW RESPONSE: {response.text}")

        if not response.parsed:
            logger.warning(f"Gemini returned no parsed response for category validation. Raw: {response.text}")
            return CategoryValidationResponse(category="unknown")

        parsed = CategoryValidationResponse.model_validate(response.parsed)

        return parsed

    @retry(
        retry=retry_if_exception_type(ServerError),
        wait=wait_exponential(multiplier=RETRY_MULTIPLIER, min=RETRY_MIN_WAIT, max=RETRY_MAX_WAIT),
        stop=stop_after_attempt(RETRY_ATTEMPTS),
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

        response = await self._generate_response(prompt, JobContractResponse.model_json_schema())

        if not response.parsed:
            return []

        parsed_response = JobContractResponse.model_validate(response.parsed)
        return parsed_response.contracts
