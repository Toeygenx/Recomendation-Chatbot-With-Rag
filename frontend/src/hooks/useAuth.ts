import { useState, useEffect } from "react";

const AUTH_KEY = "gened_admin_auth";

export const useAuth = () => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const authStatus = localStorage.getItem(AUTH_KEY);
    setIsAuthenticated(authStatus === "true");
    setIsLoading(false);
  }, []);
//for now jaa
  const login = (password: string): boolean => {
    if (password === "root") {
      localStorage.setItem(AUTH_KEY, "true");
      setIsAuthenticated(true);
      return true;
    }
    return false;
  };

  const logout = () => {
    localStorage.removeItem(AUTH_KEY);
    setIsAuthenticated(false);
  };

  return { isAuthenticated, isLoading, login, logout };
};
