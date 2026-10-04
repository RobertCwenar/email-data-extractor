from fastapi import APIRouter

from database.database import Database
from database.queries import QueryDB

router = APIRouter()

db = Database()
db_query = QueryDB(db)


@router.get("/offers")
def get_offers():
    return db_query.get_offers()
