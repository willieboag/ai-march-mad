import os
import streamlit as st
from datetime import datetime
import psycopg2

# Retrieve password from Streamlit secrets
password = st.secrets["database"]["DBPASSWD"]

# Connect to the database using psycopg2
#cstring = f'postgresql://postgres:{password}@db.orpsyqcvpzvjrpwjmdbe.supabase.co:5432/postgres'
cstring = f'postgresql://postgres.orpsyqcvpzvjrpwjmdbe:{password}@aws-0-us-west-1.pooler.supabase.com:5432/postgres'

# Update to use psycopg2 for creating a connection and executing queries
conn = psycopg2.connect(cstring)
cursor = conn.cursor()

# Define the initial 16 teams
teams = [
    "01 - Tom Brady", "16 - Isabella Stewart Gardner", "08 - Clara Barton", "09 - Louisa May Alcott",
    "05 - Paul Revere", "12 - Amy Poehler", "04 - Susan B. Anthony", "13 - John Cena", "06 - Emily Dickinson",
    "11 - Bobby Orr", "03 - John F. Kennedy", "14 - Abigail Adams", "07 - Ben Affleck", "10 - Chris Evans",
    "02 - David Ortiz", "15 - Nancy Kerrigan"
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
cursor.execute("""
    SELECT COUNT(*) FROM information_schema.tables 
    WHERE table_name = 'predictions';
""")
table_exists = cursor.fetchone()[0] > 0

if not table_exists:
    cursor.execute('''
        CREATE TABLE predictions (
            username VARCHAR(100),
            round INTEGER,
            match VARCHAR(255),
            winner VARCHAR(100),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

def save_predictions(username, round, matchups, winners):
    """Saves the predictions to the database and session state."""
    timestamp = datetime.now()
    for match, winner in zip(matchups, winners):
        cursor.execute('''
            INSERT INTO predictions (username, round, match, winner, timestamp)
            VALUES (%s, %s, %s, %s, %s)
        ''', (username, round, f"{match[0]} vs {match[1]}", winner, timestamp))
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
                st.subheader("Your Full Prediction Path: ")
                st.write(str(st.session_state.all_predictions))  # Print all selected winners in order
            else:
                next_round()

    if st.button("Reset Bracket"):
        reset_bracket()

# Close the cursor and connection when the app is closed
cursor.close()
conn.close()
