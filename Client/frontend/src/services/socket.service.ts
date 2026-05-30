// socket.service.ts

import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class SocketService {

  private socket!: WebSocket;

  public messages$ = new Subject<any>();

  connect() {
    console.log('inside socket loop');
    
    this.socket = new WebSocket('ws://localhost:8000/ws');

    this.socket.onopen = () => {
      console.log('Connected to backend');
    };

    this.socket.onmessage = (event) => {

      const data = JSON.parse(event.data);

      this.messages$.next(data);
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