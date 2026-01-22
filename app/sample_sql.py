from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
 
DATABASE_URL = "postgresql+psycopg2://retool:npg_a2Dck4vBuXpH@ep-young-dust-afizvmne.c-2.us-west-2.retooldb.com/retool?sslmode=require"
 
def check_db():
    try:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except OperationalError as e:
        print("DB error:", e)
        return False
 
if check_db():
    print("✅ DB is reachable")
else:
    print("❌ DB is not reachable")