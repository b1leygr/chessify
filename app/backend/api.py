from flask import Flask
import random

app = Flask(__name__)

positions = ['rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR', 
             'r1bqk2r/pppp1ppp/2n2n2/b3p3/2B1P3/2N2N2/PPPP1PPP/R1BQKR1',
             'r1bqk1nr/pppp1ppp/2n5/4p3/1b1PP3/5N2/PPP2PPP/RNBQKB1R',
             '2rqk2r/1b1p1ppp/p1n1pn2/1p6/1b1NP3/2N1BP2/PPPQ2PP/2KR1B1R',
             '8/8/3k4/8/2K5/8/8/8',]

@app.route('/api/play')
def play():
    randomFEN = random.choice(positions)
    return {'FEN': randomFEN}

@app.route('/api/calibrate')
def calibrate():
    return None