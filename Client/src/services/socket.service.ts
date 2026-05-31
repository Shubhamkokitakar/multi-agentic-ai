// socket.service.ts

import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';
import { environment } from '../environments/environment';


@Injectable({
  providedIn: 'root'
})
export class SocketService {

  private socket!: WebSocket;

  public messages$ = new Subject<any>();
  baseUrl = `${environment.wsUrl}/auth/signup`

  connect() {
    console.log('inside socket loop');
    
    this.socket = new WebSocket(this.baseUrl);

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