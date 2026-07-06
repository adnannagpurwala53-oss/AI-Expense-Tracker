from flask import Flask, render_template, request, jsonify, send_file
import json
import os
from datetime import datetime
import io
import csv
app = Flask(__name__)
DATA_FILE = "data/expenses.json"

# Auto-categorization keywords
CATEGORIES = {
    "Food & Dining": ["food", "restaurant", "pizza", "burger", "lunch", "dinner", "breakfast", "coffee", "cafe", "eat", "meal", "grocery", "groceries", "snack", "drink", "juice", "tea"],
    "Transport": ["uber", "taxi", "bus", "train", "metro", "fuel", "petrol", "gas", "transport", "travel", "fare", "cab", "auto", "rickshaw", "flight", "ticket"],
    "Shopping": ["shopping", "clothes", "shirt", "shoes", "amazon", "flipkart", "mall", "store", "purchase", "bought", "dress", "pants", "accessories"],
    "Entertainment": ["movie", "netflix", "spotify", "game", "cinema", "concert", "show", "entertainment", "fun", "party", "event", "music", "subscription"],
    "Health": ["doctor", "medicine", "pharmacy", "hospital", "gym", "fitness", "health", "medical", "clinic", "tablet", "vitamin", "supplement"],
    "Education": ["book", "course", "tuition", "school", "college", "university", "study", "class", "tutorial", "fee", "education", "stationery"],
    "Bills & Utilities": ["electricity", "water", "internet", "phone", "bill", "rent", "wifi", "mobile", "recharge", "utility", "maintenance"],
    "Other": []
}

# Budget limits per category (default values in currency)
DEFAULT_BUDGETS = {
    "Food & Dining": 5000,
    "Transport": 2000,
    "Shopping": 3000,
    "Entertainment": 1500,
    "Health": 2000,
    "Education": 3000,
    "Bills & Utilities": 4000,
    "Other": 1000
}
def load_expenses():
    """Load expenses from JSON file"""
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return []
def save_expenses(expenses):
    """Save expenses to JSON file"""
    with open(DATA_FILE, "w") as f:
        json.dump(expenses, f, indent=2)
def categorize_expense(description):
    """Auto-categorize expense based on description keywords"""
    description_lower = description.lower()
    for category, keywords in CATEGORIES.items():
        if category == "Other":
            continue
        for keyword in keywords:
            if keyword in description_lower:
                return category
    return "Other"
def generate_ai_suggestions(expenses, budgets):
    """Generate AI budget suggestions based on spending patterns"""
    if not expenses:
        return ["Start adding expenses to get personalized budget suggestions!"]
    suggestions = []

    # Calculate spending per category
    category_spending = {}
    for expense in expenses:
        cat = expense["category"]
        category_spending[cat] = category_spending.get(cat, 0) + expense["amount"]

    # Check overspending
    for category, spent in category_spending.items():
        budget = budgets.get(category, DEFAULT_BUDGETS.get(category, 1000))
        percentage = (spent / budget) * 100
        if percentage >= 100:
            suggestions.append(
                f"🚨 You've exceeded your {category} budget by AED {spent - budget:.0f}! "
                f"Consider cutting back immediately."
            )
        elif percentage >= 80:
            suggestions.append(
                f"⚠️ You've used {percentage:.0f}% of your {category} budget. "
                f"Only AED {budget - spent:.0f} remaining — spend carefully."
            )
        elif percentage >= 50:
            suggestions.append(
                f"📊 {category} is at {percentage:.0f}% of budget. You're on track!"
            )

    # Find highest spending category
    if category_spending:
        top_category = max(category_spending, key=category_spending.get)
        top_amount = category_spending[top_category]
        suggestions.append(
            f"💡 Your highest spending is on {top_category} (AED {top_amount:.0f}). "
            f"Look for ways to reduce this."
        )

    # Total spending insight
    total_spent = sum(category_spending.values())
    total_budget = sum(budgets.get(cat, DEFAULT_BUDGETS.get(cat, 1000)) 
                      for cat in DEFAULT_BUDGETS)
    savings = total_budget - total_spent
    if savings > 0:
        suggestions.append(
            f"✅ Great job! You're AED {savings:.0f} under your total budget. "
            f"Consider saving or investing this amount."
        )
    else:
        suggestions.append(
            f"❌ You've overspent your total budget by AED {abs(savings):.0f}. "
            f"Review your expenses and cut unnecessary costs."
        )

    # Frequency insight
    if len(expenses) > 5:
        daily_avg = total_spent / max(len(set(e["date"] for e in expenses)), 1)
        suggestions.append(
            f"📈 Your average daily spending is AED {daily_avg:.0f}. "
            f"Project this over 30 days: AED {daily_avg * 30:.0f}/month."
        )
    return suggestions if suggestions else ["Keep tracking your expenses for better insights!"]
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/add", methods=["POST"])
def add_expense():
    """Add a new expense"""
    try:
        data = request.json
        description = data.get("description", "").strip()
        amount = float(data.get("amount", 0))
        date = data.get("date", datetime.now().strftime("%Y-%m-%d"))

        if not description:
            return jsonify({"error": "Description is required"}), 400
        if amount <= 0:
            return jsonify({"error": "Amount must be greater than 0"}), 400

        expenses = load_expenses()

        new_expense = {
            "id": len(expenses) + 1,
            "description": description,
            "amount": amount,
            "category": categorize_expense(description),
            "date": date,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        expenses.append(new_expense)
        save_expenses(expenses)

        return jsonify({
            "success": True,
            "expense": new_expense
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/expenses", methods=["GET"])
def get_expenses():
    """Get all expenses"""
    expenses = load_expenses()
    return jsonify(expenses)

@app.route("/delete/<int:expense_id>", methods=["DELETE"])
def delete_expense(expense_id):
    """Delete an expense by ID"""
    expenses = load_expenses()
    expenses = [e for e in expenses if e["id"] != expense_id]
    save_expenses(expenses)
    return jsonify({"success": True})

@app.route("/summary", methods=["GET"])
def get_summary():
    """Get spending summary and AI suggestions"""
    expenses = load_expenses()
    budgets = DEFAULT_BUDGETS.copy()

    # Calculate category totals
    category_totals = {}
    for expense in expenses:
        cat = expense["category"]
        category_totals[cat] = category_totals.get(cat, 0) + expense["amount"]

    # Generate AI suggestions
    suggestions = generate_ai_suggestions(expenses, budgets)

    return jsonify({
        "category_totals": category_totals,
        "budgets": budgets,
        "suggestions": suggestions,
        "total_spent": sum(e["amount"] for e in expenses),
        "total_budget": sum(budgets.values()),
        "expense_count": len(expenses)
    })

@app.route("/export", methods=["GET"])
def export_csv():
    """Export expenses as CSV"""
    expenses = load_expenses()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Description", "Amount", "Category", "Date"])

    for expense in expenses:
        writer.writerow([
            expense["id"],
            expense["description"],
            expense["amount"],
            expense["category"],
            expense["date"]
        ])

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="expenses.csv"
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)