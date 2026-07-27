// Webcam.jsx
import Webcam from 'react-webcam'
import React, { useRef, useCallback, useState } from 'react'
import './Capture.css'

const Capture = ({ updateBoard, getBoardImage, loading, moveLegal, gameOver, reset }) => {
    const videoConstraints = {
    width: 1920,
    height: 1080,
    facingMode: "user"
    };
    const webcamRef = React.useRef(null);
    const imageRef = React.useRef(getBoardImage);
    const capture = React.useCallback(
        (action) => {
            const imageSrc = webcamRef.current.getScreenshot();
            if (imageSrc) {               
                switch(action) {
                    case 'move':
                        getBoardImage(imageSrc, 'move');   
                        console.log("Success");                              
                        break;
                    case 'calibrate':
                        getBoardImage(imageSrc, 'calibrate');                          
                        console.log("Success"); 
                        break;
                }
            }
        },
        [webcamRef, getBoardImage]
    );

    const [calibrateDisabled, setCalibrateDisabled] = useState(false);
    const handleClick = (button) => {
        if (button.id === 'move') {
            capture('move');
        }
        else if (button.id === 'calibrate') {
            capture('calibrate');
            setCalibrateDisabled(true);
        }
    }
    
    const handleReset = () => {
        reset();
        setCalibrateDisabled(false);
    }

    return (
        <>
            <div class="webcam">
            <Webcam 
            ref={webcamRef}
            screenshotFormat="image/jpeg"
            videoConstraints={videoConstraints}
            width={768}
            height={432}
            forceScreenshotSourceSize={true}
            audio={false}
            onUserMediaError={(error) => {
            console.error("Camera access denied or unavailable:", error);}}
            />
            <div class = "interact">
                <button class="buttons" id="move" onClick={(e) => handleClick(e.target)} disabled={loading || gameOver}>
                    Move
                </button>
                <button class="buttons" id="calibrate" onClick={(e) => handleClick(e.target)} disabled={loading || gameOver || calibrateDisabled}>
                    Calibrate
                </button>
            </div>
            <div>
            <p style={{ visibility: moveLegal === false ? 'visible' : 'hidden' }}>
                Illegal move made! Please try again.
            </p>
            <button style={{ background: 'none', border: 'none', color: 'blue', textDecoration: 'underline', cursor: 'pointer', fontSize: '16px', width: 'fit-content' }} onClick={handleReset} disabled={loading}>
                Reset Game
            </button>
            </div>
            </div>
        </>
    );
}

export default Capture