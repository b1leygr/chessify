import { useState, useEffect } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from './assets/vite.svg'
import heroImg from './assets/hero.png'
import './App.css'
import Board from './components/Board'
import Capture from './components/Capture'
import testImages from './testimages.json';
import { io } from 'socket.io-client';

const socket = io({
  autoConnect: true,
  transports: ["websocket"],
  upgrade: false,
})

function App() {
  const [currentFEN, setCurrentFEN] = useState('8/8/8/8/8/8/8/8')
  const [loading, setLoading] = useState('');
  const [error, setError] = useState('');
  const [boardImage, setBoardImage] = useState(null);
  const [moveLegal, setMoveLegal] = useState(null);
  const [gameOver, setGameOver] = useState(false);
  console.log('testImages:', testImages);
  const testimage = testImages[Object.keys(testImages)[0]].data;
  const [isConnected, setIsConnected] = useState(socket.connected)
  const [statusMessage, setStatusMessage] = useState('Disconnected');
  const [joinStarted, setJoinStarted] = useState(false);
  const [gameID, setGameID] = useState(null);
  const [colour, setColour] = useState(null);
  const [isCalibrated, setIsCalibrated] = useState(false);
  const [gameReady, setGameReady] = useState(false);
  
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
      setStatusMessage('Match found!');
    });
    
    socket.on('calibration_successful', (data) => {
      setIsCalibrated(true);
      setCurrentFEN(data.FEN);
      setStatusMessage('Calibration successful!');
    });
    
    socket.on('calibration_complete', (data) => {
      setGameReady(true);
      setCurrentFEN(data.FEN);
      setStatusMessage('Calibration complete!');
    });

    socket.on('move_successful', (data) => {
      setCurrentFEN(data.FEN);
    });

    socket.on('game_over', (data) => {
      setCurrentFEN(data.FEN);
      setStatusMessage(data.message);
      setGameOver(true);
      alert(data.message);
    });

    return () => {
        socket.off('connect');
        socket.off('disconnect');
        socket.off('matchmaking_status');
        socket.off('game_started');
        socket.off('calibration_successful');
        socket.off('calibration_complete');
        socket.off('move_successful');
        socket.off('game_over');
      };
  }, [])

  const handleJoinClick = () => {
    setStatusMessage('Joining...');
    socket.emit('join');
    setJoinStarted(true);
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
          body: JSON.stringify({ image: imageSrc, message: action, game_id: gameID, colour: colour }),
        }
      );
      if(!response.ok){
        throw new Error('Network response error')
      }
      const data = await response.json();
      if (action === 'move') {
        if (data.message === 'Move successful!') {
          setMoveLegal(true);
          setStatusMessage('Move successful!');
        }
        else if (data.message === 'Illegal move!') {
          setMoveLegal(false);
          setStatusMessage('Illegal move! Please try again.');
        }
      }
      else if (action === 'calibrate') {
      }
    }
    catch(error) {
      setError('Failed to fetch FEN from API');
      console.error(error);
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
      setTimeout(() => {setCurrentFEN(data.FEN)}, 1000);
    } catch (error) {
      setError('Failed to fetch computer move from API');
      console.error(error);
    }
    finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setCurrentFEN('8/8/8/8/8/8/8/8');
    setBoardImage(null);
    setMoveLegal(null);
    setGameOver(false);
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
      setError('Failed to reset game in API');
      console.error(error);
    }
  }

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', flexDirection: 'column' }}>
      <div class="components">
      <Board boardPosition={currentFEN} colour={colour} />
      <Capture updateBoard={updateBoard} getBoardImage={getBoardImage} loading={loading} moveLegal={moveLegal} gameOver={gameOver} reset={handleReset} isCalibrated={isCalibrated} isMyTurn={isMyTurn()} />
      </div>
      <div> Status: {statusMessage}
      {/* <div>WebSocket Status: {isConnected ? 'Connected' : 'Disconnected'}</div> */}
      <br/>
      { !joinStarted && (
        <button onClick={handleJoinClick} style={{ width: '200px', height: '50px', alignSelf: 'center' }}>
          Join Game Room
        </button>
      )}
      { gameID && (
        <div>Game ID: {gameID} </div>
      )}
      </div>            
      </div>
      <br/>
      {/* <button style={{ width: '200px', height: '50px'}}> Join room </button> */}
{/*       {boardImage && (
        <div>
          <h3>Captured Screenshot:</h3>
          <img src={boardImage} alt="Screenshot preview"/>
        </div>
      )} */}
    </>
  )
}

export default App
