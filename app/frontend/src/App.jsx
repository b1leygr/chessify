import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from './assets/vite.svg'
import heroImg from './assets/hero.png'
import './App.css'
import Board from './components/Board'
import Capture from './components/Capture'
import testImages from './testimages.json';

function App() {
  const [currentFEN, setCurrentFEN] = useState('8/8/8/8/8/8/8/8')
  const [loading, setLoading] = useState('');
  const [error, setError] = useState('');
  const [boardImage, setBoardImage] = useState(null);
  const [moveLegal, setMoveLegal] = useState(null);
  const [gameOver, setGameOver] = useState(false);
  console.log('testImages:', testImages);
  const testimage = testImages[Object.keys(testImages)[0]].data;

  const getBoardImage = (imageSrc, action) => {
    setBoardImage(imageSrc);
    updateBoard(imageSrc, action)
    if (action === 'move') {
      if (moveLegal === true && gameOver === false) {
        getComputerMove();
      }
    }
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
          body: JSON.stringify({ image: imageSrc, message: action }),
        }
      );
      if(!response.ok){
        throw new Error('Network response error')
      }
      const data = await response.json();
      if (action === 'move') {
        if (data.message === 'Move successful!') {
          setMoveLegal(true);
          setCurrentFEN(data.FEN);
        }
        else if (data.message === 'Illegal move!') {
          setMoveLegal(false);
        }
        else if (data.message === 'Game over!') {
          setCurrentFEN(data.FEN);
          setGameOver(true);
          if (data.outcome === 'White win') {
            alert('Game over! White wins!');
          }
          else if (data.outcome === 'Black win') {
            alert('Game over! Black wins!');
          }
        }
      }
      else if (action === 'calibrate') {
        setCurrentFEN(data.FEN);
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
      });
    } 
    catch (error) {
      setError('Failed to reset game in API');
      console.error(error);
    }
  }

  return (
    <>
      <div class="components">
      <Board boardPosition={currentFEN}/>
      <Capture updateBoard={updateBoard} getBoardImage={getBoardImage} loading={loading} moveLegal={moveLegal} gameOver={gameOver} reset={handleReset} />
      </div>
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
