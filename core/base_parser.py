# Library
from modules.ai_service import AIService
from modules.db_save import Database
from modules.filter_service import FilterService
from modules.processed_cache import FileCache


class BaseParser:
    def __init__(
        self,
        ai_service: AIService,
        db_service: Database,
        filter_service: FilterService,
        processed_cache: FileCache,
    ):
        self.ai = ai_service
        self.db = db_service
        self.filter = filter_service
        self.cache = processed_cache
