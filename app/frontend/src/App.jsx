import { useState, useEffect } from 'react'
import './App.css'
import Board from './components/Board'
import Capture from './components/Capture'
import { io } from 'socket.io-client';

const socket = io({
  autoConnect: true,
  transports: ['websocket'],
  upgrade: false,
})

function App() {
  const [currentFEN, setCurrentFEN] = useState('8/8/8/8/8/8/8/8')
  const [loading, setLoading] = useState('');
  const [boardImage, setBoardImage] = useState(null);
  const [gameOver, setGameOver] = useState(false);
  const [isConnected, setIsConnected] = useState(socket.connected)
  const [statusMessage, setStatusMessage] = useState('Disconnected');
  const [joinStarted, setJoinStarted] = useState(false);
  const [computerGameStarted, setComputerGameStarted] = useState(false);
  const [gameID, setGameID] = useState(null);
  const [colour, setColour] = useState(null);
  const [isCalibrated, setIsCalibrated] = useState(false);
  const [gameMode, setGameMode] = useState(null);
  const [moveHistory, setMoveHistory] = useState([{'startSquare': '', 'endSquare': ''}]);
  const [matedKing, setMatedKing] = useState(null);
  
  useEffect(() => {
    socket.on('connect', () => {
      setIsConnected(true);
      setStatusMessage('Connected');
    });

    socket.on('disconnect', () => {
      setIsConnected(false);
      setStatusMessage('Disconnected');
    });

    socket.on('matchmaking_status', (data) => {
      setStatusMessage(data.message);
    });

    socket.on('game_started', (data) => {
      setGameID(data.game_id);
      setColour(data.colour);
      setGameMode('multiplayer');
      setStatusMessage(data.message);
    });
    
    socket.on('opponent_calibrated', (data) => {
      setCurrentFEN(data.FEN);
      setStatusMessage(data.message);
    });
    
    socket.on('calibration_complete', (data) => {
      setIsCalibrated(true);
      setCurrentFEN(data.FEN);
      setStatusMessage(data.message);
    });

    socket.on('move_complete', (data) => {
      setCurrentFEN(data.FEN);
      setMoveHistory(prevHistory => [...prevHistory, 
        {'startSquare': data.start_square,
          'endSquare': data.end_square}]);
    });

    socket.on('game_over', (data) => {
      setCurrentFEN(data.FEN);
      setStatusMessage(data.message);
      setMoveHistory(prevHistory => [...prevHistory, 
        {'startSquare': data.start_square,
          'endSquare': data.end_square}]);
      setMatedKing(data.mated_king);
      setGameOver(true);
      alert(data.message);
    });

    return () => {
        socket.off('connect');
        socket.off('disconnect');
        socket.off('matchmaking_status');
        socket.off('game_started');
        socket.off('opponent_calibrated');
        socket.off('calibration_complete');
        socket.off('move_complete');
        socket.off('game_over');
      };
  }, [])

  const handlePvPClick = () => {
    setStatusMessage('Joining...');
    socket.emit('join');
    setJoinStarted(true);
  };

    const handlePvCClick = () => {
    setStatusMessage('Computer game started');
    setGameMode('computer');
    setGameID('computer_game');
    setColour('white');
    setComputerGameStarted(true);
  };

  const isMyTurn = () => {
    if (colour === 'white' && currentFEN.split(' ')[1] === 'w') {
      return true;
    }
    else if (colour === 'black' && currentFEN.split(' ')[1] === 'b') {
      return true;
    }
    return false;
  };

  const getBoardImage = (imageSrc, action) => {
    setBoardImage(imageSrc);
    updateBoard(imageSrc, action); 
  };

  const updateBoard = async (imageSrc, action) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/${action}`, 
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            image: imageSrc,
            game_mode: gameMode,
            game_id: gameID,
            colour: colour,
          }),
        }
      );
      if(!response.ok){
        throw new Error('Network response error')
      }
      const data = await response.json();
      if (action === 'move') {
        if (data.message === 'Move successful!') {
          setStatusMessage(data.message);
          if (gameMode === 'computer') {
              setCurrentFEN(data.FEN);
              setMoveHistory(prevHistory => [...prevHistory, 
                {'startSquare': data.start_square,
                  'endSquare': data.end_square}]);
              getComputerMove();
            }
        }
        else if (data.message === 'Illegal move!') {
          setStatusMessage(`${data.message} Please try again.`);
        }
        else if (data.message === 'Game over!' && gameMode === 'computer') {
          setStatusMessage(data.message);
          setCurrentFEN(data.FEN);
          setMoveHistory(prevHistory => [...prevHistory, 
            {'startSquare': data.start_square,
              'endSquare': data.end_square}]);
          setMatedKing(data.mated_king);
          setGameOver(true);
        }
      }
      else if (action === 'calibrate') {
        if ((data.message).toUpperCase().includes(('calibration successful').toUpperCase())) {
          setIsCalibrated(true);
          setStatusMessage(data.message);
          setCurrentFEN(data.FEN);
        }
      }
    }
    catch(error) {
      console.error('Failed to fetch FEN from API', error);
    }
    finally {
      setLoading(false);
    }
  }

  const getComputerMove = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/get_computer_move', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      const data = await response.json();
      setTimeout(() => {setCurrentFEN(data.FEN),
        setStatusMessage(data.message + ` ${data.computer_move}`)}, 
        setMoveHistory(prevHistory => [...prevHistory, 
          {'startSquare': data.start_square,
            'endSquare': data.end_square}]),
         1500);
    } catch (error) {
      console.error('Failed to fetch computer move from API', error);
    }
    finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setCurrentFEN('8/8/8/8/8/8/8/8');
    setBoardImage(null);
    setGameOver(false);
    setJoinStarted(false);
    setComputerGameStarted(false);
    setGameID(null);
    setColour(null);
    setIsCalibrated(false);
    setGameMode(null);    
    setMoveHistory([{'startSquare': '', 'endSquare': ''}]);
    setMatedKing(null);
    setStatusMessage('Game reset');
    try {
      fetch('/api/reset', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ game_id: gameID }),
      });
    } 
    catch (error) {
      console.error('Failed to reset game in API', error);
    }
  }

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', flexDirection: 'column' }}>
      <div className='components'>
      <Board boardPosition={currentFEN} colour={colour} moveHistory={moveHistory} matedKing={matedKing} />
      <Capture updateBoard={updateBoard} getBoardImage={getBoardImage} 
      loading={loading} gameOver={gameOver} reset={handleReset} 
      isCalibrated={isCalibrated} isMyTurn={isMyTurn()} gameID={gameID} />
      </div>
      <div> Status: {statusMessage}
      <br/>
      { !joinStarted && !computerGameStarted && (
        <button onClick={handlePvPClick}
        style={{ width: '200px', height: '50px', alignSelf: 'center' }}
        disabled={!isConnected}>
          Play vs Player
        </button>
      )}
      {' '}
      { !joinStarted && !computerGameStarted && (
        <button onClick={handlePvCClick}
        style={{ width: '200px', height: '50px', alignSelf: 'center' }}
        disabled={!isConnected}>
          Play Computer
        </button>
      )}      
      { gameID && gameID !== 'computer_game' && (
        <div>Game ID: {gameID} </div>
      )}
      </div>            
      </div>
    </>
  )
}

export default App