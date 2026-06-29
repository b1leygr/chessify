import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from './assets/vite.svg'
import heroImg from './assets/hero.png'
import './App.css'
import Board from './components/Board'
import Capture from './components/Capture'

function App() {
  const [count, setCount] = useState(0)
  const [currentFEN, setCurrentFEN] = useState('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR')
  const [loading, setLoading] = useState('');
  const [error, setError] = useState('');

  const play = async () => {
    setLoading(true);
    try {
      const response = await fetch('api/play', 
        {
          method: 'GET',
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
      <Capture play={play}/>
      </div>
    </>
  )
}

export default App
