# Library
from modules.ai_service import AIService
from modules.db_save import Database
from modules.filter_service import FilterService


class BaseParser:
    def __init__(self, ai_service: AIService, db_service: Database, filter_service: FilterService):
        self.ai = ai_service
        self.db = db_service
        self.filter = filter_service
