// socket.service.ts (Angular)

import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class SocketService {

  private socket!: WebSocket;

  connect() {

    this.socket = new WebSocket('ws://localhost:8000/ws');

    this.socket.onopen = () => {
      console.log('Connected to backend');
    };

    this.socket.onmessage = (event) => {
      console.log('Message from backend:', event.data);
    };

    this.socket.onerror = (error) => {
      console.error('WebSocket Error:', error);
    };

    this.socket.onclose = () => {
      console.log('Socket disconnected');
    };
  }

  sendQuestion(question: string) {

    if (this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(question);
    } else {
      console.log('Socket not connected');
    }
  }
}