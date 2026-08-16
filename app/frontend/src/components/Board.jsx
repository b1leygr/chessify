// Board.jsx
import { Chessboard } from 'react-chessboard'
import './Board.css'

const Board = ({ boardPosition, colour, moveHistory, matedKing }) => {
    const customSquareStyles = {};
    const mateStyle = {
        background: 'radial-gradient(circle, rgb(233, 59, 11), rgba(233, 59, 11, 0))'
    };    
    if (moveHistory.length > 0) {
        const lastMove = moveHistory[moveHistory.length - 1];
        customSquareStyles[lastMove.startSquare] = { backgroundColor: 'rgb(170, 162, 58)' };
        customSquareStyles[lastMove.endSquare] = { backgroundColor: 'rgb(215, 220, 110)' };
    }
    if (matedKing) {
        customSquareStyles[matedKing] = mateStyle;
    }
    const chessboardOptions = {
      position: boardPosition,
      showAnimations: false,
      allowDragging: false,
      allowDragOffBoard: false,
      boardOrientation: colour,
      squareStyles: customSquareStyles,
    };
    if (boardPosition != '')
        {
        return(
            <div className='board'>
                <Chessboard options={chessboardOptions} />
                <p>
                    Current FEN:<br/> 
                    {boardPosition.split(' ')[0]}
                </p>
            </div>
        );
        }
}

export default Board;