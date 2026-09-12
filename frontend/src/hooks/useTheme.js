import { createContext, createElement, useCallback, useContext, useEffect, useState } from "react";
import { THEMES } from "../themes";

export const ThemeContext = createContext();

export function ThemeProvider({ children }) {
  const [themeName, setThemeNameState] = useState(() => {
    try {
      return localStorage.getItem("meero_theme") || "meero";
    } catch {
      return "meero";
    }
  });

  const currentTheme = THEMES[themeName] || THEMES.meero;

  const applyCssVars = useCallback((theme) => {
    const root = document.documentElement;
    Object.entries(theme.css).forEach(([key, val]) => {
      root.style.setProperty(key, val);
    });
  }, []);

  useEffect(() => {
    applyCssVars(currentTheme);
  }, [currentTheme, applyCssVars]);

  const setTheme = useCallback((name) => {
    if (!THEMES[name]) return;
    setThemeNameState(name);
    try {
      localStorage.setItem("meero_theme", name);
    } catch {
      // ignore
    }
  }, []);

  return createElement(
    ThemeContext.Provider,
    { value: { themeName, theme: currentTheme, setTheme } },
    children
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    return {
      themeName: "meero",
      theme: THEMES.meero,
      setTheme: () => {},
    };
  }
  return ctx;
}
