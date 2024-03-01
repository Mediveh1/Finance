import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

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


#
# db.execute("DROP TABLE purchases")
# db.execute("CREATE TABLE purchases ("
#            " purchase_id INTEGER PRIMARY KEY AUTOINCREMENT,datebought DATE , datesold DATE,remainingshares INTEGER,sold INTEGER ,stockname varchar(20),numberofshares INTEGER, user_id INT ,purchaseprice INTEGER, FOREIGN KEY (user_id) REFERENCES users(id))")
#


# db.execute("UPDATE users SET cash='10000'")
#

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
    """Show portfolio of stocks"""
    usreId = session["user_id"]
    # balance = db.execute(f"SELECT * FROM users")
    # transactions = db.execute(f"SELECT * FROM purchases")
    result = db.execute(
        "SELECT users.cash , purchases.remainingshares ,users.id,purchases.sold,  purchases.numberofshares,purchases.purchaseprice , purchases.stockname FROM purchases INNER JOIN   users ON users.id=purchases.user_id")

    return render_template("index.html", result=result)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")

    if request.method == "POST":

        symbol = request.form.get("symbol")
        numshares = int(request.form.get("shares"))

        if not lookup(symbol):
            return apology("No company found")

        if numshares <= 0:
            return apology("Shares must be a positive integer")
        usreId = session["user_id"]
        balance = db.execute(f"SELECT cash FROM users where id == {usreId}")
        total = lookup(symbol)["price"]
        numberOfStocksBought = balance[0]["cash"] - (total * numshares)
        if numberOfStocksBought < 0:
            return apology("You Dont Have Enough Cash")
        db.execute(f"UPDATE users SET  cash  = {numberOfStocksBought} WHERE id == {usreId}")
        db.execute("INSERT INTO purchases (stockname, numberofshares, user_id, purchaseprice) VALUES  (?,?,?,?)",
                   symbol, numshares, usreId, total)

        # Adjust remaining shares when buying

        totalshares = db.execute(
            f"SELECT SUM(numberofshares) FROM purchases WHERE stockname = ?  AND user_id = ?", symbol, usreId)
        print(totalshares)
        print(totalshares[0]['SUM(numberofshares)'])
        db.execute(
            f"UPDATE purchases SET remainingshares={totalshares[0]['SUM(numberofshares)']} WHERE  stockname={symbol} AND user_id={usreId}")

        return redirect("/")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    if request.method == "GET":
        return redirect("/")
    return apology("TODO")


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
    if request.method == "POST":
        symbol = request.form.get("symbol")

        if symbol == "":
            return apology("enter a ticker symbol")

        if lookup(symbol)["name"] == True:
            return apology("enter a valid ticker symbol")
        res = lookup(symbol)
        balance = db.execute("SELECT * FROM users")
        return render_template("quoted.html", res=res, balance=balance)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        newusername = request.form.get("newuser")
        if newusername == "":
            return apology("enter a username")
        users = db.execute("SELECT username FROM users")

        for i in users:
            if i['username'] == newusername:
                return apology("user name already exists!")
        # password
        password = request.form.get("newpassword")
        confirmpassword = request.form.get("confirmation")
        if password != confirmpassword:
            return apology("Passwords Missmatch")
        newpassword = generate_password_hash(request.form.get("newpassword"))

        db.execute(f"INSERT INTO users(username, hash) VALUES (?, ?)", newusername, newpassword)

    return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "GET":
        return render_template("sell.html")

    if request.method == "POST":
        usreId = session["user_id"]
        company = request.form.get("sellsymbol")

        checkcompany = db.execute(
            f"SELECT stockname FROM purchases WHERE stockname = '{company}' AND user_id=={usreId}")

        if company == "":
            return apology(("Enter a valid company symbol !"))

        soldshares = float(request.form.get("numberssold"))
        soldshares1 = int(soldshares)

        ownedshares = db.execute(
            f"SELECT numberofshares FROM purchases WHERE stockname='{company}' AND user_id == {usreId}")

        if soldshares <= 0 or ownedshares == None:
            return apology("You dont have enough shares")

        totalshares = db.execute(
            f"SELECT SUM(numberofshares) FROM purchases WHERE stockname='{company}' AND user_id='{usreId}'")
        totalshares1 = totalshares[0]['SUM(numberofshares)']
        if totalshares1 < soldshares:
            return apology("you dont have that much shares to sell!!!")
        remainingShares = totalshares1 - soldshares1

        db.execute(
            f"UPDATE purchases SET remainingshares='{remainingShares}' WHERE  stockname='{company}' AND  user_id='{usreId}'")

        db.execute(f"UPDATE purchases SET sold = '{soldshares1}' WHERE user_id='{usreId}'")

        balance = db.execute(f"SELECT cash FROM users WHERE id={usreId}")
        currentSharePrice = lookup(company)["price"]
        if totalshares1 < soldshares == False:
            return

        remainder = balance[0]["cash"] + (currentSharePrice * soldshares)

        db.execute(f"UPDATE users  SET cash = '{remainder}' WHERE id= {usreId}")

        return redirect("/")


if __name__ == '__main__':
    # debug=True will rerun the server whenever a change is made
    app.run(debug=True)
