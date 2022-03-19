# MTG Home Leaderboard
#### Video Demo:  https://youtu.be/Frdan8_M494
#### Description: Web Application for Magic: The Gathering tournaments
The application is split over sevaral functions including an Elo tracker and the ability to create a new tournament using the database of players that have been registered into the system.

The homepage shows a tally of the total standings of all players that have been registered into the database. The first function that I included was the ability to log a single match between two players. This runs a calculation to increase/decrease each player's Elo rating according to the formula designed by Arpad Elo. Each match is logged into the Match History database that is viewable via the Match History tab.

To create a new tournament users can select the tournament setup tab where they are prompted to create a new name for the tournament then add players until there are at least 4 competitors. Further improvements could be included to remove specific players if errors are made. It is also possible to view each of the current ongoing tournaments.

To run a tournament users use the Run Tournament tab and start the chosen tournament. This generates a table number and pairs players based on alphabetical order. This enables a pseudo-random start to the tournament. Scores are reported in the same page via the Report a result function. Tournaments can be viewed at any point via the select menu allowing for multiple tournaments to run at the same time.

Once all the results have been included the user can progress to the next round which will store wins/loss/draws and points in a central database then players are matched based on their point score with higher scoring players being paired together. Once the user decides enough rounds have been played the end tournament button can be pressed which will drop any temporary tables, commit all changes to the overall results sheet and then display the winning players of the tournament.

app.py is my the main python code for the project, elocalc.py is a function I wrote to calculate the elo change each player will have. Within the template for my html is a script for users to be able to change the order that each table is sorted in to allow for sorting by name, wins or Elo which users might find useful.

elo.db contains the databases for storing data between sessions. The history table stores every match that is entered outside of a tournament. record stores the names of all the users that are registered along with their total win, loss, draw and elo rating. matchScores contains the different options for each match to allow html pages to select from a fixed set of options.