import { useEffect, useRef, useState } from "react";

export const useWebSocket = () => {
  const [lastMessage, setLastMessage] = useState(null);
  const ws = useRef(null);

  useEffect(() => {
    const connect = () => {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${protocol}//${window.location.host}/ws/submissions`;

      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        console.log("WebSocket connected");
      };

      ws.current.onmessage = (event) => {
        setLastMessage(event);
      };

      ws.current.onclose = () => {
        console.log("WebSocket disconnected, attempting to reconnect...");
        setTimeout(connect, 5000);
      };

      ws.current.onerror = (error) => {
        console.error("WebSocket error:", error);
      };
    };

    connect();

    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, []);

  return { lastMessage };
};
