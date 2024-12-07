import threading
import os

def run_minigames():
    os.system("python minigames.py")

def run_economy():
    os.system("python economy.py")

# Create threads
minigames_thread = threading.Thread(target=run_minigames)
economy_thread = threading.Thread(target=run_economy)

# Start threads
minigames_thread.start()
economy_thread.start()

# Wait for threads to complete (optional)
minigames_thread.join()
economy_thread.join()
