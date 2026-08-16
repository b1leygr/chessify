import base64
from pathlib import Path

import chess
import chess.engine
import cv2
from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, close_room
import numpy as np
from rfdetr import RFDETRMedium

import chess_utils


app = Flask(__name__)
app.secret_key = 'test_environment'
socketio = SocketIO(
    app,
    cors_allowed_origins='*',
    logger=False,
    engineio_logger=False,
    async_mode='gevent'
    )
project_dir = Path.cwd()


try:
    import warnings
    warnings.filterwarnings('ignore', message='Converting a tensor to a Python boolean')
    print('Loading RFDETR model...')
    model = RFDETRMedium(
        pretrain_weights=str(
            project_dir
            / 'models'
            / 'rfdetr_medium_v2'
            / 'checkpoint_best_total.pth'
        ),
        num_classes=12
    )
    model.optimize_for_inference()
    print('RFDETR model loaded successfully.')
except Exception as e:
    print(f'Error loading RFDETR model: {e}')
    model = None


try:
    print('Loading Stockfish engine...')
    stockfish_path = project_dir / 'stockfish' / 'win' / 'stockfish_18.exe'
    engine = chess.engine.SimpleEngine.popen_uci(str(stockfish_path))
    engine.configure({'Skill Level': 3})
    print('Stockfish engine loaded successfully.')
except Exception as e:
    print(f'Error loading Stockfish engine: {e}')
    engine = None

print('API is running...')

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
        emit('game_started', {'game_id': game_id, 'colour': 'white', 'message': 'Match found! White'}, to=opponent_sid)
        emit('game_started', {'game_id': game_id, 'colour': 'black', 'message': 'Match found! Black'}, to=player_sid)
        print(f'Room {game_id} created with users {opponent_sid} and {player_sid}')

@app.route('/api/calibrate', methods=['POST'])
def calibrate():
    data = request.get_json()
    game_mode = data.get('game_mode')
    game_id = data.get('game_id')
    if game_mode == 'computer':
        games[game_id] = {
            'position': '8/8/8/8/8/8/8/8',
            'white': {'squares': None},
        }
    game = games[game_id]
    colour = data.get('colour')
    image = data.get('image')

    try:
        if ',' in image:
            image = image.split(',')[1]
        image = base64.b64decode(image)
        image = np.frombuffer(image, dtype=np.uint8)
        image = cv2.imdecode(image, cv2.IMREAD_COLOR)
    except Exception as e:
        print(f'Error processing image: {e}')
        return {'message': 'Error processing image'}
    
    board_grid = chess_utils.localise_and_extract(image)
    game[f'{colour}']['squares'] = chess_utils.squares_to_dict(board_grid)

    if game_mode == 'computer':
        board = chess.Board()
        game['position'] = board.fen()
        return {'message': 'Calibration successful!', 'FEN': game['position']}

    if game['white']['squares'] and game['black']['squares']:
        board = chess.Board()
        game['position'] = board.fen()
        socketio.emit('calibration_complete', 
                      {'message': 'Calibration complete!', 'FEN': game['position']}, room=game_id)
        return {'message': 'Calibration complete for both players'}

    socketio.emit('opponent_calibrated', 
                  {'message': f'{colour.capitalize()} has calibrated their board',
                   'FEN': '8/8/8/8/8/8/PPPPPPPP/RNBQKBNR'
                   if colour == 'white'
                   else 'rnbqkbnr/pppppppp/8/8/8/8/8/8'},
                  to=game[f'{ "black" if colour == "white" else "white" }']['id'])

    return {'message': f'{colour.capitalize()} calibration successful, waiting for opponent',
            'FEN': '8/8/8/8/8/8/PPPPPPPP/RNBQKBNR'
            if colour == 'white'
            else 'rnbqkbnr/pppppppp/8/8/8/8/8/8'}

@app.route('/api/move', methods=['POST'])
def move():
    data = request.get_json()
    game_mode = data.get('game_mode')
    game_id = data.get('game_id')
    game = games[game_id]
    colour = data.get('colour')
    image = data.get('image')

    try:
        if ',' in image:
            image = image.split(',')[1]
        image = base64.b64decode(image)
        image = np.frombuffer(image, dtype=np.uint8)
        image = cv2.imdecode(image, cv2.IMREAD_COLOR)
    except Exception as e:
        print(f'Error processing image: {e}')
        return {'message': 'Error processing image'}

    for square in game[f'{colour}']['squares']:
        game[f'{colour}']['squares'][square]['predictions'] = []
    detections = model.predict(image)
    chess_utils.predict_board(game[f'{colour}']['squares'], detections)
    fens_to_try = chess_utils.get_fen_permutations(game[f'{colour}']['squares'])
    board = chess.Board(game['position'])
    print(f'Board FEN: {board.board_fen()}')
    print(f'Predicted FENs: {fens_to_try}')

    for move in board.legal_moves:
        board.push(move)
        start_square = chess.square_name(move.from_square)
        end_square = chess.square_name(move.to_square)        
        if board.board_fen() in fens_to_try:
            game['position'] = board.fen()
            break
        board.pop()
    else:
        return {'message': 'Illegal move!'}

    outcome = board.outcome()
    if outcome is not None:
        winner = 'Draw' if outcome.winner is None else ('White' if outcome.winner == chess.WHITE else 'Black')
        if winner != 'Draw':
            mated_king = chess.square_name(board.king(chess.BLACK if winner == 'White' else chess.WHITE))
        else:
            mated_king = None
        message = f'Game over! {winner} wins' if outcome.winner is not None else 'Game over! Draw'
        if game_mode == 'computer':
            return {'message': message,
                    'FEN': game['position'],
                    'start_square': start_square, 'end_square': end_square, 'mated_king': mated_king}
        socketio.emit('game_over', {'message': message,
                                    'FEN': game['position'],
                                    'start_square': start_square, 'end_square': end_square, 'mated_king': mated_king},
                                    room=game_id)
        return {'message': 'Game over!'}
    else:
        if game_mode == 'computer':
            return {'message': 'Move successful!',
                    'FEN': game['position'],
                    'start_square': start_square, 'end_square': end_square}
        socketio.emit('move_complete',
                      {'FEN': game['position'],
                       'start_square': start_square, 'end_square': end_square},
                       room=game_id)

    return {'message': 'Move successful!'}

@app.route('/api/get_computer_move', methods=['POST'])
def get_computer_move():
    board = chess.Board(games['computer_game']['position'])

    try:
        print('Fetching computer move...')
        result = engine.play(board, chess.engine.Limit(time=0.1))
        print(f'Computer move: {result.move}')

        board.push(result.move)
        start_square = chess.square_name(result.move.from_square)
        end_square = chess.square_name(result.move.to_square)
        games['computer_game']['position'] = board.fen()

        outcome = board.outcome()
        mated_king = None
        if outcome is not None:
            winner = 'Draw' if outcome.winner is None else ('White' if outcome.winner == chess.WHITE else 'Black')
            if winner != 'Draw':
                mated_king = chess.square_name(board.king(chess.BLACK if winner == 'White' else chess.WHITE))
            message = f'Game over! {winner} wins' if outcome.winner is not None else 'Game over! Draw'
        message = 'Computer move fetched!'
        return {'message': message, 'FEN': games['computer_game']['position'],
                'start_square': start_square, 'end_square': end_square,'mated_king': mated_king,
                'computer_move': str(result.move)}
    except Exception as e:
        print(f'Error getting computer move: {e}')
        return {'message': 'Error getting computer move'}

@socketio.on('disconnect')
def disconnect():
    print(f'Client has disconnected: {request.sid}')
    try:
        if games['computer_game']:
            games.pop('computer_game')
            print('Computer game terminated due to disconnection')
            return None
    except KeyError:
        pass

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

@app.route('/api/reset', methods=['POST'])
def reset():
    data = request.get_json()
    game_id = data.get('game_id')

    if game_id in games:
        games.pop(game_id)
        return {'message': 'Reset successful!'}
    
    return {'message': 'No active game to reset'}

if __name__ == '__main__':
    host = '127.0.0.1'
    port = 5000
    try:
        socketio.run(app, host=host, port=port, debug=True, log_output=True, use_reloader=False)
    except KeyboardInterrupt:
        print('Shutting down server...')
    finally:
        if engine:
            try:
                engine.quit()
                print('Server shut down successfully.')
            except chess.engine.EngineTerminatedError:
                print('Engine already terminated.')
            except Exception as e:
                print(f'Error shutting down engine: {e}')
            