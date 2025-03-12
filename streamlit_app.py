import os
import streamlit as st
from datetime import datetime
from sqlalchemy import create_engine, text

# Load database credentials securely from Streamlit secrets
try:
    username = st.secrets["database"]["DB_USERNAME"]
    password = st.secrets["database"]["DB_PASSWD"]
    dbname   = st.secrets["database"]["DBNAME"]  # Example: 'your-db-host.com'
except KeyError as e:
    st.error(f"Missing database configuration: {e}")
    st.stop()

# Create the correct SQLAlchemy connection string for Oracle
DATABASE_URL = f"oracle+cx_oracle://{username}:{password}@{dbname}"
oracle_engine = create_engine(DATABASE_URL)


# Define the initial 16 teams
teams = [
    "01 - Tom Brady",
    "16 - Isabella Stewart Gardner",
    "08 - Clara Barton",
    "09 - Louisa May Alcott",
    "05 - Paul Revere",
    "12 - Amy Poehler",
    "04 - Susan B. Anthony",
    "13 - John Cena",
    "06 - Emily Dickinson",
    "11 - Bobby Orr",
    "03 - John F. Kennedy",
    "14 - Abigail Adams",
    "07 - Ben Affleck",
    "10 - Chris Evans",
    "02 - David Ortiz",
    "15 - Nancy Kerrigan"
]

def generate_matchups(teams):
    """Generates matchups in a bracket order."""
    return [(teams[i], teams[i+1]) for i in range(0, len(teams), 2)]

# Initialize session state for tracking rounds, username, and predictions
if "round" not in st.session_state:
    st.session_state.round = 1
    st.session_state.matchups = generate_matchups(teams)
    st.session_state.winners = []
    st.session_state.username = ""
    st.session_state.username_submitted = False
    st.session_state.all_predictions = []  # Stores all winners for tracking

# Database setup (Check if table exists before creating)
with oracle_engine.connect() as conn:
    result = conn.execute(text("""
        SELECT COUNT(*) FROM user_tables WHERE table_name = 'PREDICTIONS'
    """))
    table_exists = result.scalar() > 0
    
    if not table_exists:
        conn.execute(text('''
            CREATE TABLE predictions (
                username VARCHAR2(100),
                round NUMBER,
                match VARCHAR2(255),
                winner VARCHAR2(100),
                timestamp TIMESTAMP DEFAULT SYSTIMESTAMP
            )
        '''))
        conn.commit()

def save_predictions(username, round, matchups, winners):
    """Saves the predictions to the database and session state."""
    timestamp = datetime.now()
    with oracle_engine.connect() as conn:
        for match, winner in zip(matchups, winners):
            conn.execute(text('''
                INSERT INTO predictions (username, round, match, winner, timestamp)
                VALUES (:username, :round, :match, :winner, :timestamp)
            '''), {
                "username": username,
                "round": round,
                "match": f"{match[0]} vs {match[1]}",
                "winner": winner,
                "timestamp": timestamp
            })
            st.session_state.all_predictions.append(winner)  # Store all predictions
        conn.commit()

def next_round():
    """Moves to the next round with the selected winners."""
    if len(st.session_state.winners) == len(st.session_state.matchups):
        save_predictions(st.session_state.username, st.session_state.round, st.session_state.matchups, st.session_state.winners)
        st.session_state.matchups = generate_matchups(st.session_state.winners)
        st.session_state.winners = []
        st.session_state.round += 1
        st.rerun()

def reset_bracket():
    """Resets the bracket to the first round."""
    st.session_state.round = 1
    st.session_state.matchups = generate_matchups(teams)
    st.session_state.winners = []
    st.session_state.all_predictions = []  # Clear all stored predictions
    st.rerun()

# User input for username
if not st.session_state.username_submitted:
    st.session_state.username = st.text_input("Enter your username:")
    if st.button("Submit Username"):
        if st.session_state.username:
            st.session_state.username_submitted = True
            st.rerun() 
    st.stop()

# Display the bracket UI only if the username has been submitted
if st.session_state.username_submitted:
    st.title("AI March Madness Bracket")
    st.subheader(f"Round {st.session_state.round}")

    winners = []
    for match in st.session_state.matchups:
        winner = st.radio(f"Select winner: {match[0]} vs {match[1]}", [match[0], match[1]], key=f"match_{match[0]}_{match[1]}")
        winners.append(winner)

    if st.button("Next Round"):
        if len(winners) == len(st.session_state.matchups):
            st.session_state.winners = winners
            if len(winners) == 1:
                # Final winner reached
                st.success(f"🏆 The final winner is {winners[0]}! 🏆")
                save_predictions(st.session_state.username, st.session_state.round, st.session_state.matchups, st.session_state.winners)
                
                # Display all 15 predictions
                st.subheader("Your Full Prediction Path:")
                st.write(str(st.session_state.all_predictions))  # Print all selected winners in order
            else:
                next_round()

    if st.button("Reset Bracket"):
        reset_bracket()
