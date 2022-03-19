from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from datetime import datetime

from elocalc import elo_adjustment

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure Library to use SQLite database
db = SQL("sqlite:///elo.db")


@app.route("/", methods=["GET"])
def index():
    # """Show the ELO leaderboard on the homepage"""

    # Fetch the ELO data from the sql database
    leaderboard = db.execute("SELECT * FROM record ORDER BY elo DESC")

    return render_template("index.html", leaderboard=leaderboard)


@app.route("/register", methods=["POST"])
def register():

    # """Register a new player"""
    if request.method == "POST":
        Player = request.form.get("newPlayer")
        if Player == '':
            flash('Error: Please enter a player name')
            return redirect("/")
        newPlayerCheck = db.execute("SELECT COUNT(name) FROM record WHERE name=?", Player)

        if newPlayerCheck[0]["COUNT(name)"] == 0:
            db.execute("INSERT INTO record (name, win, loss, draw, elo) VALUES(?, 0, 0, 0, 1000)", Player)
            flash(Player+' registered successfully')
            return redirect("/")

        flash('Error: A player with this name is already registered')
        return redirect("/")
    else:
        flash('Error: Please submit the player name again')
        return redirect("/")


@app.route("/report", methods=["GET","POST"])
def report():
    # Report a result into the elo database
    players = db.execute("SELECT DISTINCT name FROM record ORDER BY name")
    if request.method == "POST":
        player1Name = request.form.get("player1")
        player2Name = request.form.get("player2")
        player1Score = request.form.get("player1Score")
        player2Score = request.form.get("player2Score")
        if player1Name == "" or player2Name == "" or player1Name == None or player2Name == None:
            flash('Error: Please enter a name for all players')
            return render_template("report.html", players=players)
        if player1Name == player2Name:
            flash('Error: Players cant play against themselves')
            return render_template("report.html", players=players)
        if player1Score == None or player2Score == None:
            flash('Error: Please enter a score for all players')
            return render_template("report.html", players=players)


        registered1 = db.execute("SELECT COUNT(name) FROM record WHERE name=?", player1Name)
        registered2 = db.execute("SELECT COUNT(name) FROM record WHERE name=?", player2Name)
        player1EloTemp = db.execute("SELECT elo FROM record WHERE name=?", player1Name)
        player2EloTemp = db.execute("SELECT elo FROM record WHERE name=?", player2Name)
        player1Elo = player1EloTemp[0]['elo']
        player2Elo = player2EloTemp[0]['elo']

        # get date and time
        now = datetime.now()
        dtString = now.strftime("%d/%m/%Y %H:%M:%S")

        # Check if the player names exist in the database
        if registered1[0]["COUNT(name)"] == 0:
            flash('Error: '+player1Name+' does not exist')
            return render_template("report.html", players=players)
        if registered2[0]["COUNT(name)"] == 0:
            flash('Error: '+player2Name+' does not exist')
            return render_template("report.html", players=players)

        # Check nobody did some weird stuff to submit incorrect scores
        scores = [0, 1, 2]
        if player1Score == None or player2Score == None:
            flash('Error: Player must have a score')
            return render_template("report.html", players=players)
        if int(player1Score) not in scores or int(player2Score) not in scores:
            flash('Error: Scores must be 0, 1 or 2')
            return render_template("report.html", players=players)

        # Modify the match history to include this result
        db.execute("INSERT INTO history (firstname, firstresult, secondname, secondresult, timestamp) VALUES (?, ?, ?, ?, ?)", player1Name, player1Score, player2Name, player2Score, dtString)

        # Modify each players record to reflect the changes
        if player1Score > player2Score: # Where player 1 is the winner
            db.execute("UPDATE record SET win=win+1, elo=? WHERE name=?", elo_adjustment(player1Elo, player2Elo, 1), player1Name)
            db.execute("UPDATE record SET loss=loss+1, elo=? WHERE name=?", elo_adjustment(player2Elo, player1Elo, 0), player2Name)
        elif player2Score > player1Score: # Where player 2 is the winner
            db.execute("UPDATE record SET win=win+1, elo=? WHERE name=?", elo_adjustment(player2Elo, player1Elo, 1), player2Name)
            db.execute("UPDATE record SET loss=loss+1, elo=? WHERE name=?", elo_adjustment(player1Elo, player2Elo, 0), player1Name)
        else: # Where both players draw is the winner
            db.execute("UPDATE record SET draw=draw+1, elo=? WHERE name=?", elo_adjustment(player1Elo, player2Elo, 0.5), player1Name)
            db.execute("UPDATE record SET draw=draw+1, elo=? WHERE name=?", elo_adjustment(player2Elo, player1Elo, 0.5), player2Name)

        # Redirect user to home page
        flash('Results logged successfully')
        return redirect("/")

    else:
        # Got here by GET not POST
        players = db.execute("SELECT DISTINCT name FROM record ORDER BY name")
        return render_template("report.html", players=players)


@app.route("/history", methods=["GET"])
def history():
    # """Show the match history on the history page"""

    # Fetch the matches from the sql database
    history = db.execute("SELECT * FROM history")

    return render_template("history.html", history=history)


@app.route("/create", methods=["GET", "POST"])
def create():
    players = db.execute("SELECT name FROM record")
    tournament = db.execute("SELECT name FROM tournaments WHERE type=1")
    if request.method == "POST":
        newTournament = request.form.get("create")
        # If user does not enter a name for the new tournament
        if newTournament == None or newTournament == "":
            tournamentName = "Overall Results"
            data = db.execute("SELECT * FROM record")
            flash('Error: Please enter a name for the tournament')
            return render_template("tournamentsetup.html", players=players, data=data, tournamentName=tournamentName, tournament=tournament)
        # Find out if a tournament with this name already exists
        if " " in newTournament:
            tournamentName = "Overall Results"
            data = db.execute("SELECT * FROM record")
            flash('Error: Tournament names cannot include a space')
            return render_template("tournamentsetup.html", players=players, data=data, tournamentName=tournamentName, tournament=tournament)

        tableNames = db.execute("SELECT name FROM tournaments WHERE name=?", newTournament)
        if len(tableNames) == 1:
            tournamentName = newTournament
            data = db.execute("SELECT * FROM ?", newTournament)
            flash('Error: A tournament with this name already exists')
            return render_template("tournamentsetup.html", players=players, data=data, tournamentName=tournamentName, tournament=tournament)
        else:
            # Create a tournament and display it to the user
            db.execute("CREATE TABLE ? (name TEXT, win INTEGER, loss INTEGER, draw INTEGER, points INTEGER, elo INTEGER, id INTEGER)", newTournament)
            db.execute("INSERT INTO tournaments (name, type) VALUES (?, 1)", newTournament)
            data = db.execute("SELECT * FROM ?", newTournament)
            tournament = db.execute("SELECT name FROM tournaments WHERE type=1")
            flash('Tournament created successfully')
            return render_template("tournamentsetup.html", data=data, players=players, tournamentName=newTournament, tournament=tournament)
    else:
        # Got here by GET not POST
        tournamentName = "Overall Results"
        data = db.execute("SELECT * FROM record")
        return render_template("tournamentsetup.html", players=players, data=data, tournamentName=tournamentName, tournament=tournament)

@app.route("/change", methods=["GET","POST"])
def change():
    players = db.execute("SELECT name FROM record")
    tournament = db.execute("SELECT name FROM tournaments WHERE type=1")
    if request.method == "POST":
        tournamentName = request.form.get("change")
        # If user does not select a tournament value
        if tournamentName == None:
            tournamentName = "Overall Results"
            data = db.execute("SELECT * FROM record")
            flash('Error: Please select a tournament')
            return render_template("tournamentsetup.html", players=players, data=data, tournamentName=tournamentName, tournament=tournament)
        # If a user selects the option Overall Results
        if tournamentName == "Overall Results":
            data = db.execute("SELECT * FROM record")
            flash('Overall results selected')
            return render_template("tournamentsetup.html", players=players, data=data, tournamentName=tournamentName, tournament=tournament)
        # Display the tournament that the user selected
        else:
            data = db.execute("SELECT * FROM ?", tournamentName)
            flash(tournamentName+' selected')
            return render_template("tournamentsetup.html", players=players, data=data, tournamentName=tournamentName, tournament=tournament)

    else:
        # Got here by GET not POST
        tournamentName = "Overall Results"
        data = db.execute("SELECT * FROM record")
        return render_template("tournamentsetup.html", players=players, data=data, tournamentName=tournamentName, tournament=tournament)


@app.route("/add", methods=["POST"])
def add():
    players = db.execute("SELECT name FROM record")
    tournament = db.execute("SELECT name FROM tournaments WHERE type=1")
    if request.method == "POST":
        playerName = request.form.get("add")
        if playerName == None:
            tournamentName = "Overall Results"
            data = db.execute("SELECT * FROM record")
            flash('Error: Please select a player name')
            return render_template("tournamentsetup.html", players=players, data=data, tournamentName=tournamentName, tournament=tournament)
        playerElo = db.execute("SELECT * FROM record WHERE name=?", playerName)
        tournamentName = request.form.get("select")
        if tournamentName == None:
            data = db.execute("SELECT * FROM record")
            flash('Error: Please select a tournament name')
            return render_template("tournamentsetup.html", players=players, data=data, tournamentName=tournamentName, tournament=tournament)
        alreadyAdded = db.execute("SELECT COUNT(name) FROM ? WHERE name=?", tournamentName, playerName)
        # If the user does not select a value for player or tournament
        if tournamentName == None:
            tournamentName = "Overall Results"
            data = db.execute("SELECT * FROM record")
            flash('Error: Please select a tournament name')
            return render_template("tournamentsetup.html", players=players, data=data, tournamentName=tournamentName, tournament=tournament)
        if alreadyAdded[0]["COUNT(name)"] != 0:
            tournamentName = "Overall Results"
            data = db.execute("SELECT * FROM record")
            flash('Error: This player has already been added to this tournament')
            return render_template("tournamentsetup.html", players=players, data=data, tournamentName=tournamentName, tournament=tournament)
        db.execute("INSERT INTO ? (name, win, loss, draw, points, elo) VALUES (?, 0, 0, 0, 0, ?)", tournamentName, playerName, playerElo[0]["elo"])
        data = db.execute("SELECT * FROM ?", tournamentName)
        flash(playerName+' has been successfully added to '+tournamentName)
        return render_template("tournamentsetup.html", players=players, data=data, tournamentName=tournamentName, tournament=tournament)
    else:
        tournamentName = "Overall Results"
        data = db.execute("SELECT * FROM record")
        return render_template("tournamentsetup.html", players=players, data=data, tournamentName=tournamentName, tournament=tournament)


@app.route("/run", methods=["GET", "POST"])
def run():
    tournament = db.execute("SELECT name FROM tournaments WHERE type=1")
    tracker = db.execute("SELECT name FROM tournaments WHERE type=2")
    scores = db.execute("SELECT * FROM matchScores")
    if request.method == "POST":
        if request.form.get("pick") == None:
            data = db.execute("SELECT * FROM record")
            flash('Error: Please select a tournament name')
            return render_template("run.html", tournament=tournament, tracker=tracker, scores=scores)
        tournamentName = (request.form.get("pick"))+"Tracker"
        playerNames = db.execute("SELECT name FROM ?", tournamentName.replace('Tracker',"",1))
        if len(playerNames) < 4:
            data = db.execute("SELECT * FROM record")
            flash('Error: Please add at least 4 players to the tournament')
            return render_template("run.html", tournament=tournament, tracker=tracker, scores=scores)

        tableNames = db.execute("SELECT COUNT(name) FROM tournaments WHERE name=?", tournamentName)
        if tableNames[0]["COUNT(name)"] == 1:
            data = db.execute("SELECT * FROM record")
            flash('Error: A tournament named '+tournamentName.replace("Tracker","",1)+' already exists')
            return render_template("run.html", tournament=tournament, tracker=tracker, scores=scores)
        # Create a table to store the results from each round.
        db.execute("CREATE TABLE ? (round INTEGER, tableNumber INTEGER, player1 TEXT, player2 TEXT, player1score INTEGER, player2score INTEGER, player1points INTEGER, player2points INTEGER, points INTEGER)", tournamentName)
        db.execute("INSERT INTO tournaments (name, type) VALUES (?, 2)", tournamentName)

        # For row in setup tournament, insert each name into the tracker
        names = db.execute("SELECT * FROM ?", (request.form.get("pick")))
        nameCounttemp = db.execute("SELECT COUNT(name) FROM ?", (request.form.get("pick")))
        nameCount = nameCounttemp[0]["COUNT(name)"]
        count = 0

        # Populate the tournament tracker with all participants
        while count < nameCount:
            db.execute("INSERT INTO ? (round, player1, player1points) VALUES (1, ?, ?)", tournamentName, names[count]["name"], names[count]["points"])
            count += 1
        # add a bye if there is an odd number of players
        if (nameCount %2) != 0:
            db.execute("INSERT INTO ? (round, player1, player1points) VALUES (1, ?, ?)", tournamentName, "BYE", "0")

        # pair players
        names = db.execute("SELECT * FROM ? ORDER BY player1", tournamentName)
        count = 0
        nameCounttemp = db.execute("SELECT COUNT(player1) FROM ?", tournamentName)
        nameCount = nameCounttemp[0]["COUNT(player1)"]
        while count < nameCount:
            # Tried to remove this step and make half of the table but it doesnt allow for adding a BYE player.
            # Also makes it easier for each player to find their name if it can be sorted alphabetically for player 1
            if count < (nameCount / 2):
                db.execute("UPDATE ? SET player2=?, player2points=?, tableNumber=? WHERE player1=?", tournamentName, names[nameCount -(count+1)]["player1"], names[nameCount -(count+1)]["player1points"], count+1, names[count]["player1"])
            else:
                db.execute("UPDATE ? SET player2=?, player2points=?, tableNumber=? WHERE player1=?", tournamentName, names[nameCount -(count+1)]["player1"], names[nameCount -(count+1)]["player1points"], nameCount-(count), names[count]["player1"])
            count +=1

        data = db.execute("SELECT * FROM ?", tournamentName)
        players = db.execute("SELECT DISTINCT player1 FROM ? ORDER BY player1", tournamentName)
        tournament = db.execute("SELECT name FROM tournaments WHERE type=1")
        tracker = db.execute("SELECT name FROM tournaments WHERE type=2")
        flash('Tournament created successfully')
        return render_template("run.html", data=data, tournamentName=tournamentName, tournament=tournament, tracker=tracker, scores=scores, players=players)
    else:
        tournamentName = "Select a tournament"
        data = db.execute("SELECT * FROM record")
        return render_template("run.html", tournament=tournament, tracker=tracker, scores=scores)


@app.route("/select", methods=["GET", "POST"])
def select():
    tournament = db.execute("SELECT name FROM tournaments WHERE type=1")
    tracker = db.execute("SELECT name FROM tournaments WHERE type=2")
    scores = db.execute("SELECT * FROM matchScores")
    if request.method == "POST":
        tournamentName = request.form.get("select")

        if tournamentName == None:
            data = db.execute("SELECT * FROM record")
            flash('Error: Please select a tournament name')
            return render_template("run.html", tournament=tournament, tracker=tracker, scores=scores)
        players = db.execute("SELECT DISTINCT player1 FROM ? ORDER BY player1", tournamentName)
        tableNames = db.execute("SELECT name FROM tournaments WHERE name=?", tournamentName)
        if len(tableNames) != 1:
            data = db.execute("SELECT * FROM record")
            flash('Error '+tournamentName+' does not exist')
            return render_template("run.html", tournament=tournament, tracker=tracker, scores=scores, players=players)

        data = db.execute("SELECT * FROM ?", tournamentName)
        players = db.execute("SELECT DISTINCT player1 FROM ? ORDER BY player1", tournamentName)
        flash(tournamentName+' selected')
        return render_template("run.html", data=data, tournamentName=tournamentName, tournament=tournament, tracker=tracker, scores=scores, players=players)
    else:
        tournamentName = "Select a tournament"
        data = db.execute("SELECT * FROM record")
        return render_template("run.html", data=data, tournamentName=tournamentName, tournament=tournament, tracker=tracker, scores=scores)


@app.route("/reportTournament", methods=["POST"])
def reportTournament():
    tournament = db.execute("SELECT name FROM tournaments WHERE type=1")
    tracker = db.execute("SELECT name FROM tournaments WHERE type=2")
    scores = db.execute("SELECT * FROM matchScores")
    if request.method == "POST":
        player1score = request.form.get("player1Score")
        player1name = request.form.get("player1")
        player2score = request.form.get("player2Score")
        player2name = request.form.get("player2")
        tournamentName = request.form.get("select")
        if tournamentName == None:
            flash('Error: Please enter a tournament name')
            return render_template("run.html", tournament=tournament, tracker=tracker, scores=scores)
        players = db.execute("SELECT DISTINCT player1 FROM ? ORDER BY player1", tournamentName)
        data = db.execute("SELECT * FROM ?", tournamentName)
        if player1name == "" or player2name == "" or player1name == None or player2name == None:
            flash('Error: Please enter a name for all players')
            return render_template("run.html", data=data, tournamentName=tournamentName, tournament=tournament, tracker=tracker, scores=scores, players=players)
        if player1name == player2name:
            flash('Error: Players cant play against themselves')
            return render_template("run.html", data=data, tournamentName=tournamentName, tournament=tournament, tracker=tracker, scores=scores, players=players)
        if player1score == None or player2score == None:
            flash('Error: Please enter a score for all players')
            return render_template("run.html", data=data, tournamentName=tournamentName, tournament=tournament, tracker=tracker, scores=scores, players=players)


        currentRoundtemp = db.execute("SELECT MAX(round) FROM ?", tournamentName)
        currentRound = currentRoundtemp[0]["MAX(round)"]
        if player1score is not None or player2score is not None:
            if player1score > player2score:
                db.execute("UPDATE ? SET player1score=?, player2score=? WHERE player1=? AND round=?", tournamentName, player1score, player2score, player1name, currentRound)
                db.execute("UPDATE ? SET player2score=?, player1score=? WHERE player1=? AND round=?", tournamentName, player1score, player2score, player2name, currentRound)
            elif player2score > player1score:
                db.execute("UPDATE ? SET player1score=?, player2score=? WHERE player1=? AND round=?", tournamentName, player1score, player2score, player1name, currentRound)
                db.execute("UPDATE ? SET player2score=?, player1score=? WHERE player1=? AND round=?", tournamentName, player1score, player2score, player2name, currentRound)
            else:
                db.execute("UPDATE ? SET player1score=?, player2score=? WHERE player1=? AND round=?", tournamentName, player1score, player2score, player1name, currentRound)
                db.execute("UPDATE ? SET player2score=?, player1score=? WHERE player1=? AND round=?", tournamentName, player1score, player2score, player2name, currentRound)
        else:
            flash('Error: A result has already been added for this pair')
            return redirect("/")
    players = db.execute("SELECT DISTINCT player1 FROM ? ORDER BY player1", tournamentName)
    data = db.execute("SELECT * FROM ?", tournamentName)
    flash('Result entered successfully')
    return render_template("run.html", data=data, tournamentName=tournamentName, tournament=tournament, tracker=tracker, scores=scores, players=players)


@app.route("/newRound", methods=["POST"])
def newRound():
    tournament = db.execute("SELECT name FROM tournaments WHERE type=1")
    tracker = db.execute("SELECT name FROM tournaments WHERE type=2")
    scores = db.execute("SELECT * FROM matchScores")
    if request.method == "POST":
        tournamentName = request.form.get("select")
        if tournamentName == None:
            flash('Error: Please enter a tournament name')
            return render_template("run.html")
        players = db.execute("SELECT DISTINCT player1 FROM ? ORDER BY player1", tournamentName)
        currentRoundtemp = db.execute("SELECT MAX(round) FROM ?", tournamentName)
        currentRound = currentRoundtemp[0]["MAX(round)"]+1
        names = db.execute("SELECT * FROM ? WHERE round=?", tournamentName, currentRound-1)
        nameCounttemp = db.execute("SELECT COUNT(player1) FROM ? WHERE round=?", tournamentName, currentRound-1)
        nameCount = nameCounttemp[0]["COUNT(player1)"]
        count = 0

        # Populate the new round with all participants and update the points based on results
        while count < nameCount:
            player1elotemp = db.execute("SELECT * FROM record WHERE name=?", names[count]["player1"])
            player1score = names[count]["player1score"]
            player1elo = player1elotemp[0]["elo"]
            player2elotemp = db.execute("SELECT * FROM record WHERE name=?", names[count]["player2"])
            player2score = names[count]["player2score"]
            player2elo = player2elotemp[0]["elo"]
        # If player1score or player2score are None then display an error saying a score is missing
            if player1score == None or player2score == None:
                flash("Error: All results must be entered")
                return render_template("run.html", tournamentName=tournamentName, tournament=tournament, tracker=tracker, scores=scores, players=players)
            if player1score > player2score:
                db.execute("INSERT INTO ? (round, player1, player1points) VALUES (?, ?, ?)", tournamentName, currentRound, names[count]["player1"], int(names[count]["player1points"])+3)
                db.execute("UPDATE ? SET win=win+1, points=points+3 WHERE name=?", tournamentName.replace('Tracker','',1), names[count]["player1"])
                db.execute("UPDATE record SET elo=? WHERE name=?", elo_adjustment(player1elo, player2elo, 1), names[count]["player1"])
            elif player1score == player2score:
                db.execute("INSERT INTO ? (round, player1, player1points) VALUES (?, ?, ?)", tournamentName, currentRound, names[count]["player1"], int(names[count]["player1points"])+1)
                db.execute("UPDATE ? SET draw=draw+1, points=points+1 WHERE name=?", tournamentName.replace('Tracker','',1), names[count]["player1"])
                db.execute("UPDATE record SET elo=? WHERE name=?", elo_adjustment(player1elo, player2elo, 0.5), names[count]["player1"])
            else:
                db.execute("INSERT INTO ? (round, player1, player1points) VALUES (?, ?, ?)", tournamentName, currentRound, names[count]["player1"], names[count]["player1points"])
                db.execute("UPDATE ? SET loss=loss+1 WHERE name=?", tournamentName.replace('Tracker','',1), names[count]["player1"])
                db.execute("UPDATE record SET elo=? WHERE name=?", elo_adjustment(player1elo, player2elo, 0), names[count]["player1"])
            count += 1

        # re-pair by points, avoiding rematches how?

        count = 0
        names = db.execute("SELECT * FROM ? WHERE round=? ORDER BY player1points DESC", tournamentName, currentRound)
        while count < nameCount:
            # Tried to remove this step and make half of the table but it doesnt allow for adding a BYE player.
            # Also makes it easier for each player to find their name if it can be sorted alphabetically for player 1
            if count % 2 == 0:
                # Find if there is a duplicate match
                # duplicate = db.execute("SELECT COUNT(player1) FROM ? WHERE player1=? AND player2=?",tournamentName, names[count]["player1"], names[count+1]["player1"])
                # if duplicate == 0: # If no duplicate go ahead and pair them
                db.execute("UPDATE ? SET player2=?, player2points=? WHERE player1=? AND round=?", tournamentName, names[count+1]["player1"], names[count+1]["player1points"], names[count]["player1"], currentRound)
            else:
                db.execute("UPDATE ? SET player2=?, player2points=? WHERE player1=? AND round=?", tournamentName, names[count-1]["player1"], names[count-1]["player1points"], names[count]["player1"], currentRound)

            # Assign tables to each pairing
            db.execute("UPDATE ? SET tableNumber=? WHERE player1=? AND round=?", tournamentName, int(round((count+2)/2)), names[count]["player1"], currentRound)
            count +=1


    # return the view to the original page
    players = db.execute("SELECT DISTINCT player1 FROM ? ORDER BY player1", tournamentName)
    data = db.execute("SELECT * FROM ? WHERE round=? OR round=?", tournamentName, currentRound-1, currentRound)
    flash('Starting round '+str(currentRound)+' in '+tournamentName)
    return render_template("run.html", data=data, tournamentName=tournamentName, tournament=tournament, tracker=tracker, scores=scores, players=players)

@app.route("/endTournament", methods=["POST"])
def endTournament():
    tournament = db.execute("SELECT name FROM tournaments WHERE type=1")
    tracker = db.execute("SELECT name FROM tournaments WHERE type=2")
    scores = db.execute("SELECT * FROM matchScores")
    tournamentName = request.form.get("select")
    if tournamentName == None:
        flash('Error: Please enter a tournament name')
        return render_template("run.html")
    players = db.execute("SELECT DISTINCT name FROM ? ORDER BY name", tournamentName)
    if request.method == "POST":
        currentRoundtemp = db.execute("SELECT MAX(round) FROM ?", tournamentName+'Tracker')
        currentRound = currentRoundtemp[0]["MAX(round)"]
        names = db.execute("SELECT * FROM ?", tournamentName)
        trackerNames = db.execute("SELECT * FROM ? WHERE round=?", tournamentName+'Tracker', currentRound)
        nameCounttemp = db.execute("SELECT COUNT(name) FROM ?", tournamentName)
        nameCount = nameCounttemp[0]["COUNT(name)"]
        count = 0
        while count < nameCount:
            print(count)
            player1elotemp = db.execute("SELECT * FROM record WHERE name=?", trackerNames[count]["player1"])
            print(player1elotemp)
            player1elo = player1elotemp[0]["elo"]
            print(player1elo)
            player2elotemp = db.execute("SELECT * FROM record WHERE name=?", trackerNames[count]["player2"])
            print(player2elotemp)
            player2elo = player2elotemp[0]["elo"]
            print(player2elo)
            player1score = trackerNames[count]["player1score"]
            print(player1score)
            player2score = trackerNames[count]["player2score"]
            print(player2score)
            if player1score == None or player2score == None:
                flash("Error: All results must be entered")
                return render_template("run.html", tournamentName=tournamentName, tournament=tournament, tracker=tracker, scores=scores, players=players)
            if player1score > player2score:
                db.execute("UPDATE ? SET win=win+1, points=points+3 WHERE name=?", tournamentName, names[count]["name"])
                db.execute("UPDATE record SET elo=? WHERE name=?", elo_adjustment(player1elo, player2elo, 1), names[count]["name"])
            elif player1score == player2score:
                db.execute("UPDATE ? SET draw=draw+1, points=points+1 WHERE name=?", tournamentName, names[count]["name"])
                db.execute("UPDATE record SET elo=? WHERE name=?", elo_adjustment(player1elo, player2elo, 0.5), names[count]["name"])
            else:
                db.execute("UPDATE ? SET loss=loss+1 WHERE name=?", tournamentName, names[count]["name"])
                db.execute("UPDATE record SET elo=? WHERE name=?", elo_adjustment(player1elo, player2elo, 0), names[count]["name"])
            names = db.execute("SELECT * FROM ?", tournamentName)
            playerName = names[count]["name"]
            winCount = names[count]["win"]
            lossCount = names[count]["loss"]
            drawCount = names[count]["draw"]
            db.execute("UPDATE record SET win=win+?, loss=loss+?, draw=draw+? WHERE name=?", int(winCount), int(lossCount), int(drawCount), playerName)
            count += 1
        db.execute("DROP TABLE ?", tournamentName+"Tracker")
        db.execute("DELETE FROM tournaments WHERE name=?", tournamentName+"Tracker")
    data = db.execute("SELECT * FROM ? ORDER BY points DESC", tournamentName)
    return render_template("standings.html", tournament=tournament, data=data)