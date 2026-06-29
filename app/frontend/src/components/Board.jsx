// Board.jsx
import { Chessboard } from 'react-chessboard'
import './Board.css'

const Board = ({ boardPosition }) => {
    const chessboardOptions = {
      position: boardPosition,
      showAnimations: false,
      allowDragging: false,
      allowDragOffBoard: false,
    };
    if (boardPosition != '')
        {
        return(
            <div class = "board">
                <Chessboard options={chessboardOptions} />
                <p>
                    Current FEN:<br/> 
                    {boardPosition}
                </p>
            </div>
        );
        }
}

export default Board;