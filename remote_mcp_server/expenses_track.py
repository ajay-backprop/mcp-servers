import random
from fastmcp import FastMCP
import os
import sqlite3
import tempfile

# DB_PATH = os.path.join(os.path.dirname(__file__), "expenses.db")
# CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

TEMP_DIR = tempfile.gettempdir()
DB_PATH = os.path.join(TEMP_DIR, "expenses.db")

print("DB PATH =", DB_PATH)

mcp = FastMCP("ajay-ExpenseTracker")

# try:
#     remote_server = FastMCP.as_proxy("https://expense-trackk.fastmcp.app/mcp", name="remote-tracker")
#     mcp.mount(remote_server) 
#     print("✓ Remote proxy successfully mounted!")
# except Exception as e:
#     print(f"⚠️ Remote proxy connect nahi ho paya: {e}")

def init_db():
    with sqlite3.connect(DB_PATH) as c:

        # Updated expenses table to handle both expenses and credits/income
        c.execute("""
            CREATE TABLE IF NOT EXISTS expenses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('expense', 'credit')),
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                note TEXT DEFAULT ''
            )
        """)
        # Added budgets table
        c.execute("""
            CREATE TABLE IF NOT EXISTS budgets(
                category TEXT PRIMARY KEY,
                amount REAL NOT NULL
            )
        """)

        c.execute(
            "INSERT OR IGNORE INTO expenses(date, type, amount, category) VALUES (?, ?, ?, ?)",
            ("2000-01-01", "expense", 0, "test")
        )
        c.execute("DELETE FROM expenses WHERE category='test'")

init_db()


@mcp.tool()
def add_expense(date: str, amount: float, category: str, subcategory: str = "", note: str = ""):
    """Add a new expense entry (money spent) to the database."""
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            "INSERT INTO expenses(date, type, amount, category, subcategory, note) VALUES (?, 'expense', ?, ?, ?, ?)",
            (date, amount, category, subcategory, note)
        )
        return {"status": "success", "id": cur.lastrowid, "message": "Expense added successfully"}
    

@mcp.tool()
def list_expenses(start_date: str, end_date: str):
    """List all entries (expenses and credits) within an inclusive date range."""
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            """
            SELECT id, date, type, amount, category, subcategory, note
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY date ASC, id ASC
            """,
            (start_date, end_date)
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


@mcp.tool()
def summarize(start_date: str, end_date: str, category: str = None):
    """Summarize expenses and credits by category within an inclusive date range."""
    with sqlite3.connect(DB_PATH) as c:
        query = """
            SELECT type, category, SUM(amount) AS total_amount
            FROM expenses
            WHERE date BETWEEN ? AND ?
        """
        params = [start_date, end_date]

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " GROUP BY type, category ORDER BY category ASC"

        cur = c.execute(query, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    

@mcp.tool()
def add_credit(date: str, amount: float, category: str, subcategory: str = "", note: str = ""):
    """Add a credit entry (income, refund, or cash influx) to the database."""
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            "INSERT INTO expenses(date, type, amount, category, subcategory, note) VALUES (?, 'credit', ?, ?, ?, ?)",
            (date, amount, category, subcategory, note)
        )
        return {"status": "success", "id": cur.lastrowid, "message": "Credit added successfully"}

@mcp.tool()
def edit_entry(entry_id: int, date: str = None, type: str = None, amount: float = None, category: str = None, subcategory: str = None, note: str = ""):
    """Edit an existing entry (expense or credit) by its ID. Provide only fields that need updates."""
    with sqlite3.connect(DB_PATH) as c:
        # Check if entry exists
        cur = c.execute("SELECT id FROM expenses WHERE id = ?", (entry_id,))
        if not cur.fetchone():
            return {"status": "error", "message": f"Entry with ID {entry_id} not found"}

        # Build dynamic update query
        updates = []
        params = []
        if date is not None:
            updates.append("date = ?")
            params.append(date)
        if type is not None:
            if type not in ('expense', 'credit'):
                return {"status": "error", "message": "Type must be either 'expense' or 'credit'"}
            updates.append("type = ?")
            params.append(type)
        if amount is not None:
            updates.append("amount = ?")
            params.append(amount)
        if category is not None:
            updates.append("category = ?")
            params.append(category)
        if subcategory is not None:
            updates.append("subcategory = ?")
            params.append(subcategory)
        if note is not None:
            updates.append("note = ?")
            params.append(note)

        if not updates:
            return {"status": "error", "message": "No parameters provided to update"}

        params.append(entry_id)
        query = f"UPDATE expenses SET {', '.join(updates)} WHERE id = ?"
        c.execute(query, params)
        return {"status": "success", "message": f"Entry {entry_id} updated successfully"}
    
@mcp.tool()
def delete_entry(entry_id: int):
    """Delete an entry (expense or credit) from the database using its ID."""
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute("DELETE FROM expenses WHERE id = ?", (entry_id,))
        if c.total_changes == 0:
            return {"status": "error", "message": f"Entry with ID {entry_id} not found"}
        return {"status": "success", "message": f"Entry {entry_id} deleted successfully"}
    

@mcp.tool()
def set_budget(category: str, amount: float):
    """Set or update a monthly budget limit for a specific category."""
    with sqlite3.connect(DB_PATH) as c:
        c.execute(
            """
            INSERT INTO budgets (category, amount) 
            VALUES (?, ?)
            ON CONFLICT(category) DO UPDATE SET amount = excluded.amount
            """,
            (category, amount)
        )
        return {"status": "success", "message": f"Budget for '{category}' set to {amount}"}


@mcp.tool()
def get_budgets():
    """Retrieve all current category budgets and limits."""
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute("SELECT category, amount FROM budgets")
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    
    
@mcp.resource("expense://categories", mime_type="application/json")
def categories():
    # Read fresh each time so you can edit the file without restarting
    with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    # mcp.run(transport = "http", host="0.0.0.0", port=8001)
    mcp.run()



# import sys
# import httpx
# from fastmcp import FastMCP

# # 1. Local server banayein jisse Claude Desktop ya Inspector jud sake (stdio par)
# mcp = FastMCP("ajay-ExpenseTracker-Bridge")


# BEARER_TOKEN = "fmcp_-gwf5enJiTOxyb14QrN-_Jw0T0ZBelAQWyHxWArtj9o"


# # Aapke deployed remote server ka URL
# REMOTE_URL = "https://expense-trackk.fastmcp.app/mcp"

# print("🚀 Async Local Proxy Bridge Starting...", file=sys.stderr)

# # -------------------------------------------------------------------------
# # ASYNC REMOTE TOOLS DEFINITIONS
# # -------------------------------------------------------------------------

# @mcp.tool()
# async def add_expense(date: str, amount: float, category: str, subcategory: str = "", note: str = "") -> str:
#     """[Remote Cloud] Add a new expense entry (money spent) to the remote database."""
#     try:
#         async with httpx.AsyncClient() as client:
#             response = await client.post(
#                 f"{REMOTE_URL}/tools/call", 
#                 headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
#                 json={"name": "add_expense", "arguments": {"date": date, "amount": amount, "category": category, "subcategory": subcategory, "note": note}},
#                 timeout=15.0
#             )
#             return response.text
#     except Exception as e:
#         return f"❌ Remote Cloud Server Error: {e}"

# @mcp.tool()
# async def list_expenses(start_date: str, end_date: str) -> str:
#     """[Remote Cloud] List all entries (expenses and credits) within an inclusive date range from remote database."""
#     try:
#         async with httpx.AsyncClient() as client:
#             response = await client.post(
#                 f"{REMOTE_URL}/tools/call", 
#                 headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
#                 json={"name": "list_expenses", "arguments": {"start_date": start_date, "end_date": end_date}},
#                 timeout=15.0
#             )
#             return response.text
#     except Exception as e:
#         return f"❌ Remote Cloud Server Error: {e}"

# @mcp.tool()
# async def summarize(start_date: str, end_date: str, category: str = None) -> str:
#     """[Remote Cloud] Summarize expenses and credits by category from remote database."""
#     try:
#         arguments = {"start_date": start_date, "end_date": end_date}
#         if category:
#             arguments["category"] = category
            
#         async with httpx.AsyncClient() as client:
#             response = await client.post(
#                 f"{REMOTE_URL}/tools/call", 
#                 headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
#                 json={"name": "summarize", "arguments": arguments},
#                 timeout=15.0
#             )
#             return response.text
#     except Exception as e:
#         return f"❌ Remote Cloud Server Error: {e}"

# @mcp.tool()
# async def add_credit(date: str, amount: float, category: str, subcategory: str = "", note: str = "") -> str:
#     """[Remote Cloud] Add a credit entry (income, refund) to the remote database."""
#     try:
#         async with httpx.AsyncClient() as client:
#             response = await client.post(
#                 f"{REMOTE_URL}/tools/call", 
#                 headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
#                 json={"name": "add_credit", "arguments": {"date": date, "amount": amount, "category": category, "subcategory": subcategory, "note": note}},
#                 timeout=15.0
#             )
#             return response.text
#     except Exception as e:
#         return f"❌ Remote Cloud Server Error: {e}"

# @mcp.tool()
# async def edit_entry(entry_id: int, date: str = None, type: str = None, amount: float = None, category: str = None, subcategory: str = None, note: str = "") -> str:
#     """[Remote Cloud] Edit an existing entry by its ID on the remote database."""
#     try:
#         args = {"entry_id": entry_id, "note": note}
#         if date is not None: args["date"] = date
#         if type is not None: args["type"] = type
#         if amount is not None: args["amount"] = amount
#         if category is not None: args["category"] = category
#         if subcategory is not None: args["subcategory"] = subcategory

#         async with httpx.AsyncClient() as client:
#             response = await client.post(
#                 f"{REMOTE_URL}/tools/call", 
#                 headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
#                 json={"name": "edit_entry", "arguments": args},
#                 timeout=15.0
#             )
#             return response.text
#     except Exception as e:
#         return f"❌ Remote Cloud Server Error: {e}"

# @mcp.tool()
# async def delete_entry(entry_id: int) -> str:
#     """[Remote Cloud] Delete an entry from the remote database using its ID."""
#     try:
#         async with httpx.AsyncClient() as client:
#             response = await client.post(
#                 f"{REMOTE_URL}/tools/call", 
#                 headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
#                 json={"name": "delete_entry", "arguments": {"entry_id": entry_id}},
#                 timeout=15.0
#             )
#             return response.text
#     except Exception as e:
#         return f"❌ Remote Cloud Server Error: {e}"

# @mcp.tool()
# async def set_budget(category: str, amount: float) -> str:
#     """[Remote Cloud] Set or update a monthly budget limit for a specific category on remote."""
#     try:
#         async with httpx.AsyncClient() as client:
#             response = await client.post(
#                 f"{REMOTE_URL}/tools/call",
#                 headers={"Authorization": f"Bearer {BEARER_TOKEN}"}, 
#                 json={"name": "set_budget", "arguments": {"category": category, "amount": amount}},
#                 timeout=15.0
#             )
#             return response.text
#     except Exception as e:
#         return f"❌ Remote Cloud Server Error: {e}"

# @mcp.tool()
# async def get_budgets() -> str:
#     """[Remote Cloud] Retrieve all current category budgets and limits from remote."""
#     try:
#         async with httpx.AsyncClient() as client:
#             response = await client.post(
#                 f"{REMOTE_URL}/tools/call", 
#                 headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
#                 json={"name": "get_budgets", "arguments": {}},
#                 timeout=15.0
#             )
#             return response.text
#     except Exception as e:
#         return f"❌ Remote Cloud Server Error: {e}"

# if __name__ == "__main__":
#     mcp.run()