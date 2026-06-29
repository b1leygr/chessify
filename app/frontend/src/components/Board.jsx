// Board.jsx
import { Chessboard } from 'react-chessboard'

export default function Board({ boardPosition }) {
    const chessboardOptions = {
      position: boardPosition,
      showAnimations: false,
      allowDragging: false,
      allowDragOffBoard: false,
    };
    if (boardPosition != '')
        {
        return(
            <div style={{ width: '500px', margin: 'auto' }}>
                <Chessboard options={chessboardOptions} />
                <p>
                    Current FEN:<br/> 
                    {boardPosition}
                </p>
            </div>
        );
        }
}