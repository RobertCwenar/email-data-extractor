# Library
from database.inserts import InsertDB
from modules.ai_service import AIService
from modules.filter_service import FilterService
from modules.processed_cache import FileCache


class BaseParser:
    def __init__(
        self,
        ai_service: AIService,
        db_insert: InsertDB,
        filter_service: FilterService,
        processed_cache: FileCache,
    ):
        self.ai = ai_service
        self.db = db_insert
        self.filter = filter_service
        self.cache = processed_cache
