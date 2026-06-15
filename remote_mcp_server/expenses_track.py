import random
from fastmcp import FastMCP
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "expenses.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

mcp = FastMCP("ExpenseTracker")

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
    mcp.run(transport = "http", host="0.0.0.0", port=8001)
    # mcp.run()