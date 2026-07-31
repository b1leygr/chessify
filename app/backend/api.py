from gevent import monkey
monkey.patch_all()
from flask import Flask, request, session
from utils import *
from pathlib import Path
""" from rfdetr import RFDETRMedium
import base64
import chess
import chess.engine """
from flask_socketio import SocketIO, emit, join_room, close_room

app = Flask(__name__)
app.secret_key = 'test_environment'
socketio = SocketIO(app, cors_allowed_origins='*', logger=False, engineio_logger=False, async_mode='gevent')
project_dir = Path.cwd()
""" model = RFDETRMedium(pretrain_weights=str(project_dir / 'models' / 'rfdetr_medium_v2' / 'checkpoint_best_total.pth'), num_classes=12)    
model.optimize_for_inference() """

games = {}
waiting_players = []

@socketio.on('connect')
def connect():
    print(f'Client has connected: {request.sid}')  

@socketio.on('join')
def join():
    player_sid = request.sid

    if player_sid in waiting_players:
        emit('matchmaking_status', {'message': 'Already in queue'}, to=player_sid)
        return None

    if not waiting_players:
        waiting_players.append(player_sid)
        emit('matchmaking_status', {'message': 'Waiting for an opponent'})
        print(f'User {player_sid} is waiting for an opponent')
    else:
        opponent_sid = waiting_players.pop(0)
        game_id = f'game_{opponent_sid}_{player_sid}'
        join_room(game_id, sid=player_sid)
        join_room(game_id, sid=opponent_sid)

        games[game_id] = {
            'position': '8/8/8/8/8/8/8/8',
            'white': {'id': opponent_sid, 'squares': None},
            'black': {'id': player_sid, 'squares': None},
        }
        emit('game_started', {'game_id': game_id, 'colour': 'white'}, to=opponent_sid)
        emit('game_started', {'game_id': game_id, 'colour': 'black'}, to=player_sid)
        print(f'Room {game_id} created with users {opponent_sid} and {player_sid}')

@app.route('/api/calibrate', methods=['POST'])
def calibrate():
    data = request.get_json
    game_id = data.get('game_id')
    colour = data.get('colour')
    image = data.get('image')
    game = games[game_id]
    game[f'{colour}']['squares'] = squares_to_dict()

    socketio.emit('calibration_successful', 
                  {'message': f'{colour.capitalize()} calibration successful'},
                  to=game[colour]['id'])

    if game['white']['squares'] and game['black']['squares']:
        socketio.emit('calibration_complete', 
                      {'message': 'Game calibration complete'},
                      room=game_id)

@socketio.on('disconnect')
def disconnect():
    print(f'Client has disconnected: {request.sid}')
    player_sid = request.sid
    if player_sid in waiting_players:
        waiting_players.remove(player_sid)
        print(f'Waiting player disconnected: {player_sid}')
        return None

    game_to_remove = None
    for game_id, game_data in list(games.items()):
        if player_sid in (game_data['white']['id'], game_data['black']['id']):
            opponent_sid = (game_data['black']['id']
                            if game_data['white']['id'] == player_sid
                            else game_data['white']['id'])
            emit('opponent_disconnected', 
                 {'message': 'Opponent disconnected'}, 
                 to=opponent_sid)
            close_room(game_id)
            game_to_remove = game_id
            break

    if game_to_remove:
        games.pop(game_to_remove)
        print(f'Active game {game_to_remove} terminated due to disconnection')

""" @app.route('/api/move', methods=['POST'])
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
    return {'FEN': board.board_fen(), 'outcome': 'None', 'message': 'Computer move fetched!'} """

@app.route('/api/reset', methods=['POST'])
def reset():
    session['square_dict'] = None
    session['position'] = None
    return {'FEN': '8/8/8/8/8/8/8/8', 'message': 'Reset successful!'}

if __name__ == '__main__':
    host = '127.0.0.1'
    port = 5000
    socketio.run(app,host=host, port=port, debug=True, log_output=True)