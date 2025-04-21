import { toast } from "react-hot-toast";

interface WebSocketMessage {
  type: string;
  data: any;
}

type MessageHandler = (data: any) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private messageHandlers: Map<string, MessageHandler[]> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectTimeout = 1000;

  constructor() {
    this.connect();
  }

  private connect() {
    const wsUrl = import.meta.env.VITE_WS_URL;
    if (!wsUrl) {
      console.error("WebSocket URL not configured");
      return;
    }

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log("WebSocket connected");
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        const handlers = this.messageHandlers.get(message.type);
        if (handlers) {
          handlers.forEach((handler) => handler(message.data));
        }
      } catch (error) {
        console.error("Error parsing WebSocket message:", error);
      }
    };

    this.ws.onclose = () => {
      console.log("WebSocket disconnected");
      this.attemptReconnect();
    };

    this.ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      toast.error("Connection error. Retrying...");
    };
  }

  private attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        console.log(
          `Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})`
        );
        this.connect();
      }, this.reconnectTimeout * this.reconnectAttempts);
    } else {
      toast.error("Failed to connect to server. Please refresh the page.");
    }
  }

  subscribe(type: string, handler: MessageHandler) {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, []);
    }
    this.messageHandlers.get(type)?.push(handler);
  }

  unsubscribe(type: string, handler: MessageHandler) {
    const handlers = this.messageHandlers.get(type);
    if (handlers) {
      const index = handlers.indexOf(handler);
      if (index !== -1) {
        handlers.splice(index, 1);
      }
    }
  }

  send(type: string, data: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, data }));
    } else {
      console.error("WebSocket is not connected");
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

export const wsService = new WebSocketService();
