import os

from cs50 import SQL
from flask import Flask, flash, redirect, jsonify, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
import datetime
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd
from myhelpers import validate_credit

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    user_id = session["user_id"]

    transactions = db.execute("SELECT symbol, SUM(shares) AS shares, price FROM transactions WHERE user_id = ? GROUP BY symbol", user_id)
    # return jsonify(transactions)
    data = []
    for row in transactions:
        symbol = row["symbol"]
        shares = row["shares"]
        price = row["price"]

        found = lookup(symbol.upper())
        if found:
            current_price = found["price"]
            total = current_price * shares
            data.append({"symbol":symbol, "shares": shares, "price": price, "current_price": current_price, "total": total})

    cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
    # return jsonify(cash)
    user_cash = cash[0]["cash"]
    Alltotal = user_cash
    for row in data:
        Alltotal += row["total"]

    return render_template("index.html", transactions = data, user_cash = user_cash, TOTAL = Alltotal)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")

    else:
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("symbol required!")
        found = lookup(symbol.upper())
        if found == None:
            return apology("symbol not found!!")
        name = found["name"]
        symbol = found["symbol"]
        price = found["price"]
        # return jsonify(price)

        shares = request.form.get("shares")
        if not shares:
            return apology("shares required!!")
        try:
            shares = int(shares)
        except ValueError:
            return apology("Input numeric values only!")

        if shares <= 0:
            return apology("Input positive shares only!")


        total_cost = price * shares

        user_id = session["user_id"]

        cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
        # return jsonify(cash)
        user_cash = cash[0]["cash"]

        if user_cash < total_cost:
            return apology("not enough cash!")

        updated_cash = user_cash - total_cost

        db.execute("UPDATE users SET cash = ? WHERE id = ?", updated_cash, user_id)

        date = datetime.datetime.now()

        db.execute("INSERT INTO transactions(user_id, name, symbol, shares, price, date) VALUES(?,?, ?, ?,?,?)", user_id, name, symbol, shares, total_cost, date)

        flash("successfully bought!")

        return redirect("/")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user_id = session["user_id"]
    transactions = db.execute("SELECT * FROM transactions WHERE user_id = ?", user_id)
    transactions.reverse()

    return render_template("history.html", transactions = transactions)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":
        return render_template("quote.html")
    else:
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("symbol required!!")

        found = lookup(symbol.upper())
        if found == None:
            return apology("symbol not found!!")

        name = found["name"]
        symbol = found["symbol"]
        price = found["price"]

        return render_template("quoted.html", name=name, symbol=symbol, price=price)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")
    else:
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username:
            return apology("username required!")
        if not password:
            return apology("password required!")
        if not confirmation:
            return apology("please match your password!!")

        if password != confirmation:
            return apology("password doesn't match!")

        try:
            new_user = db.execute("INSERT INTO users(username, hash) VALUES(?,?)", username, generate_password_hash(confirmation))
        except:
            return apology("username already exists!")

        #*** LOG USER IN ***
        session["user_id"] = new_user

        return redirect("/")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "GET":
        user_id = session["user_id"]

        symbol = db.execute("SELECT symbol FROM transactions WHERE user_id = ? GROUP BY symbol HAVING SUM(shares)>0", user_id)
        # for row in user_shares:
        #     symbol = row["symbol"]
        return render_template("sell.html", symbols = [row["symbol"] for row in symbol])
    else:
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")

        if not symbol:
            return apology("symbol required")
        found = lookup(symbol.upper())
        if found == None:
            return apology("symbol doesn't exists")
        name = found["name"]
        symbol = found["symbol"]
        price = found["price"]

        if not shares:
            return apology("shares required!!")

        try:
            shares = int(shares)
        except ValueError:
            return apology("Input numerical values only!")

        if shares <= 0:
            return apology("Input only positive values!")

        total_stock_price = price*shares

        user_id = session["user_id"]

        user_shares = db.execute("SELECT SUM(shares) AS shares FROM transactions WHERE user_id = ? AND symbol = ?", user_id, symbol)
        user_real_shares = user_shares[0]["shares"]

        if user_real_shares < shares:
            return apology("not enough shares!")

        cash = db.execute("SELECT cash FROM users WHERE id =?", user_id)
        # return jsonify(cash)
        user_cash = cash[0]["cash"]

        updated_user_cash = user_cash + total_stock_price

        db.execute("UPDATE users SET cash = ? WHERE id =?", updated_user_cash, user_id)

        date = datetime.datetime.now()

        db.execute("INSERT INTO transactions(user_id, name, symbol, shares, price, date) VALUES(?,?,?,?,?,?)", user_id, name, symbol, (-1)*shares, price, date)

        flash("congratulations! Successfully sold")

        return redirect("/")

@app.route("/forgot", methods=["GET","POST"])
def forgot():
    if request.method == "GET":
        return render_template("forgot.html")
    else:
        if "user_id" in session:
            user_id = session["user_id"]
        else:
            username = request.form.get("username")
            if not username:
                return apology("username required!!!")

            row = db.execute("SELECT id FROM users WHERE username = ?", username)
            if len(row) != 1:
                return apology("user doesn't exists!!")
            session["user_id"] = row[0]["id"]

            password = request.form.get("password")
            confirmation = request.form.get("confirmation")

            if not password:
                return apology("password required")
            if not confirmation:
                return apology("confirm password!")
            if password != confirmation:
                return apology("password doesn't match!!")

            db.execute("UPDATE users SET hash = ? WHERE id = ?", generate_password_hash(confirmation), session["user_id"])

            #display message on the header via flash
            flash("password changed successfully!!!")

            return redirect("/")


@app.route("/addcash", methods=["GET","POST"])
@login_required
def addcash():
    if request.method == "GET":
        return render_template("addcash.html")
    else:
        addcash = request.form.get("addcash")
        card_number = request.form.get("card_number")
        if not card_number:
            return apology("credit number required!!")
        try:
            card_number = int(card_number)
        except:
            return apology("Input numeric values only!!")

        if card_number <= 0:
            return apology("Invalid length!!")

        #validating the credit card using my own implementation
        is_card_valid = validate_credit(card_number)
        if is_card_valid == "INVALID":
            return apology("Invalid credit number!!")

        if not addcash:
            return apology("cash required!!")
        try:
            addcash = int(addcash)
        except:
            return apology("Input numeric values only!")
        if addcash <= 0:
            return apology("Add only positive values!")

        user_id = session["user_id"]

        cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
        user_cash = cash[0]["cash"]

        updated_cash = user_cash + addcash

        db.execute("UPDATE users SET cash = ? WHERE id = ?", updated_cash, user_id)

        #display a success message
        flash("money added successfully")

        return redirect("/")