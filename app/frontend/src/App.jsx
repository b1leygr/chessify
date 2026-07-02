import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from './assets/vite.svg'
import heroImg from './assets/hero.png'
import './App.css'
import Board from './components/Board'
import Capture from './components/Capture'
import testImages from './testimages.json';

function App() {
  const [count, setCount] = useState(0)
  const [currentFEN, setCurrentFEN] = useState('8/8/8/8/8/8/8/8')
  const [loading, setLoading] = useState('');
  const [error, setError] = useState('');
  const [boardImage, setBoardImage] = useState(null);
  console.log('testImages:', testImages);
  const testimage = testImages[Object.keys(testImages)[0]].data;

  const getBoardImage = (imageSrc, action) => {
    setBoardImage(imageSrc);
    updateBoard(imageSrc, action)
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
      setCurrentFEN(data.FEN);
    }
    catch(error) {
      setError('Failed to fetch FEN from API');
      console.error(error);
    }
    finally {
      setLoading(false);
    }
  }

  return (
    <>
      <div class="components">
      <Board boardPosition={currentFEN}/>
      <Capture updateBoard={updateBoard} getBoardImage={getBoardImage}/>
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
