// Webcam.jsx
import Webcam from 'react-webcam'
import React, { useRef, useCallback, useState } from 'react'
import './Capture.css'

const Capture = ({ play }) => {
    const videoConstraints = {
    width: 1920,
    height: 1080,
    facingMode: "user"
    };
    const webcamRef = React.useRef(null);
    const [boardImage, setBoardImage] = useState(null);
    const capture = React.useCallback(
        (action) => {
            const imageSrc = webcamRef.current.getScreenshot();
            if (imageSrc) {
                switch(action) {
                    case 'play':
                        console.log("Success");            
                        setBoardImage(imageSrc);                        
                        play();
                        break;
                    case 'calibrate':
                        console.log("Success");
                        setBoardImage(imageSrc);  
                        // calibrate(); 
                        break;
                }
            }
        },
        [webcamRef]
    );

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
                <button class="buttons" onClick={() => capture('play')}>Play</button>
                <button class="buttons" onClick={() => capture('calibrate')}>Calibrate</button>
            </div>            
            </div>
        </>
    );
}

export default Capture