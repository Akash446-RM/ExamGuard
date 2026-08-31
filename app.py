from flask import Flask, request, render_template, session, redirect
from database import init_db, get_db
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.secret_key = "exam_guard_key"  # Required for session management


# Initialize database
init_db()


@app.route("/")
def home():
    return "Welcome to Exam Guard"


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        hashed_password = generate_password_hash(password)
        print(f"Name: {name}, Email: {email}, Password: {hashed_password}")



        connection = get_db()

        connection.execute(
            """
            INSERT INTO candidates
            (name, email, password)
            VALUES (?, ?, ?)
            """,
            (name, email, hashed_password)
        )

        connection.commit()
        connection.close()

        #return "Registration successful"
        return redirect("/login")
        
    return render_template("register.html")


# 
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        connection = get_db()

        try:
            candidate = connection.execute("""
                SELECT *
                FROM candidates
                WHERE email = ? 
            """, (email,)
            ).fetchone()

            if candidate and check_password_hash(candidate["password"], password):
         
                session["candidate_id"] = candidate["id"]
                return redirect("/dashboard")

            return "Invalid email or password"

        finally:
            connection.close()

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if 'candidate_id' not in session:
        return "Please log in first"
    
    return render_template("dashboard.html")


@app.route("/logout")
def logout():
    session.pop('candidate_id', None)
    return "Logged out successfully"



if __name__ == "__main__":
    app.run(debug=True)