import React, { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";

const shouldRenderInstantly = () => {
  if (typeof window === "undefined") return true;
  if (navigator.webdriver) return true;
  if (window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches) return true;
  return false;
};

const Typewriter = ({ text = "", speed = 8, onComplete }) => {
  const instant = shouldRenderInstantly();
  const [displayedText, setDisplayedText] = useState("");
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    if (instant) {
      onComplete?.();
      return;
    }

    if (currentIndex < text.length) {
      const timeout = setTimeout(() => {
        setDisplayedText((prev) => prev + text[currentIndex]);
        setCurrentIndex((prev) => prev + 1);
      }, speed);

      return () => clearTimeout(timeout);
    } else if (currentIndex === text.length && onComplete) {
      onComplete();
    }
  }, [currentIndex, text, speed, onComplete, instant]);

  if (instant) {
    return <ReactMarkdown>{text}</ReactMarkdown>;
  }

  return <ReactMarkdown>{displayedText}</ReactMarkdown>;
};


export default Typewriter;

