def elo_adjustment(playerElo, opponentElo, result):
    # Step 1 calculate the expected win percentage based on the current elo for each player
    expectedWin = 1 / (1 + (10 ** ((opponentElo-playerElo)/400)))
    return (int(playerElo + (32 *(result - expectedWin))))