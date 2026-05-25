import { useEffect, useState } from "react";
import ReactMarkdown from 'react-markdown';

const Typewriter = ({ text, speed = 10, onComplete }) => {
  const [displayedText, setDisplayedText] = useState("");
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    if (currentIndex < text.length) {
      const timeout = setTimeout(() => {
        setDisplayedText(prev => prev + text[currentIndex]);
        setCurrentIndex(prev => prev + 1);
      }, speed);

      return () => clearTimeout(timeout);
    } else if (currentIndex === text.length && onComplete) {
       onComplete();
    }
  }, [currentIndex, text, speed, onComplete]);

  return <ReactMarkdown>{displayedText}</ReactMarkdown>;
};

export default Typewriter;
