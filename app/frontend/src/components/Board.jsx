// Board.jsx
import { Chessboard } from 'react-chessboard'
import './Board.css'

const Board = ({ boardPosition, colour }) => {
    const chessboardOptions = {
      position: boardPosition,
      showAnimations: false,
      allowDragging: false,
      allowDragOffBoard: false,
      boardOrientation: colour,
    };
    if (boardPosition != '')
        {
        return(
            <div class = "board">
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