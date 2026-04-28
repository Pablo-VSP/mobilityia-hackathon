import { useState, useEffect, useRef } from 'react';

/**
 * Reveals text word-by-word with a natural typing speed.
 * Starts immediately when `text` changes from empty to non-empty.
 */
export function useTypingEffect(text: string, speed = 30): { displayed: string; done: boolean } {
  const [displayed, setDisplayed] = useState('');
  const [done, setDone] = useState(false);
  const indexRef = useRef(0);

  useEffect(() => {
    if (!text) {
      setDisplayed('');
      setDone(false);
      indexRef.current = 0;
      return;
    }

    indexRef.current = 0;
    setDisplayed('');
    setDone(false);

    const interval = setInterval(() => {
      indexRef.current += 1;
      if (indexRef.current >= text.length) {
        setDisplayed(text);
        setDone(true);
        clearInterval(interval);
      } else {
        setDisplayed(text.slice(0, indexRef.current));
      }
    }, speed);

    return () => clearInterval(interval);
  }, [text, speed]);

  return { displayed, done };
}
