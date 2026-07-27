from flask import Flask, request, session
from utils import *
from pathlib import Path
from rfdetr import RFDETRMedium
import base64
import chess
import chess.engine

app = Flask(__name__)
app.secret_key = 'test_environment'
project_dir = Path.cwd()
model = RFDETRMedium(pretrain_weights=str(project_dir / 'models' / 'rfdetr_medium_v2' / 'checkpoint_best_total.pth'), num_classes=12)    
model.optimize_for_inference()

@app.route('/api/move', methods=['POST'])
def move():
    data = request.get_json()
    image = data.get('image')
    image = image.split(',')[1]
    image = base64.b64decode(image)
    image = np.frombuffer(image, dtype=np.uint8)
    image = cv2.imdecode(image, cv2.IMREAD_COLOR)
    for square in session['square_dict']:
        session['square_dict'][square]['piece'], session['square_dict'][square]['score'] = None, None
    predictions = model.predict(image)
    predict_board(session['square_dict'], predictions)
    fen = dict_to_fen(session['square_dict'])
    board = chess.Board(session['position'])
    for move in board.legal_moves:
        board.push(move)
        if board.board_fen() == fen:
            session['position'] = board.fen()
            break
        board.pop()
    else:
        session['position'] = board.fen()
        return {'FEN': board.board_fen(), 'outcome': 'None', 'message': 'Illegal move!'}
    if board.outcome() is not None:
        outcome = board.outcome()
        if outcome.winner is None:
            return {'FEN': board.board_fen(), 'outcome': 'Draw', 'message': 'Game over!'}
        elif outcome.winner == chess.WHITE:
            return {'FEN': board.board_fen(), 'outcome': 'White win', 'message': 'Game over!'}
        else:
            return {'FEN': board.board_fen(), 'outcome': 'Black win', 'message': 'Game over!'}  
    return {'FEN': board.board_fen(), 'outcome': 'None', 'message': 'Move successful!'}

@app.route('/api/calibrate', methods=['POST'])
def calibrate():
    data = request.get_json()
    image = data.get('image')
    image = image.split(',')[1]
    image = base64.b64decode(image)
    image = np.frombuffer(image, dtype=np.uint8)
    image = cv2.imdecode(image, cv2.IMREAD_COLOR)
    blur = preprocess(image)
    canny = autocanny(blur)
    dilated = dilate (canny)
    points = find_contour(dilated)
    corners = find_corners(points)
    warped, M_inv = warp(image, corners)
    blur = preprocess(warped)
    canny = autocanny(blur)
    closed = close(canny)
    lines = hough_lines(closed)
    h, v = sort_lines(lines)
    intersections = find_intersections(h, v)
    clustered_points = cluster_intersections(intersections)
    corners = find_corners(clustered_points)
    squares = get_squares(corners, M_inv)
    session['square_dict'] = squares_to_dict(squares)
    predictions = model.predict(image)
    predict_board(session['square_dict'], predictions)
    fen = dict_to_fen(session['square_dict'])
    board = chess.Board()
    board.set_board_fen(fen)
    session['position'] = board.fen()
    return {'FEN': fen, 'message': 'Calibration successful!'}

@app.route('/api/get_computer_move', methods=['POST'])
def get_computer_move():
    board = chess.Board(session['position'])
    with chess.engine.SimpleEngine.popen_uci(str(project_dir / 'stockfish' / 'win' / 'stockfish_18.exe')) as engine:
        engine.configure({"Skill Level": 3})
        result = engine.play(board, chess.engine.Limit(time=0.1))
        board.push(result.move)
    session['position'] = board.fen()
    if board.outcome() is not None:
        outcome = board.outcome()
        if outcome.winner is None:
            return {'FEN': board.board_fen(), 'outcome': 'Draw', 'message': 'Game over!'}
        elif outcome.winner == chess.WHITE:
            return {'FEN': board.board_fen(), 'outcome': 'White win', 'message': 'Game over!'}
        else:
            return {'FEN': board.board_fen(), 'outcome': 'Black win', 'message': 'Game over!'}
    return {'FEN': board.board_fen(), 'outcome': 'None', 'message': 'Computer move fetched!'}

@app.route('/api/reset', methods=['POST'])
def reset():
    session['square_dict'] = None
    session['position'] = None
    return {'FEN': '8/8/8/8/8/8/8/8', 'message': 'Reset successful!'}