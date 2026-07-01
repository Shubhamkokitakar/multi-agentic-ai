// socket.service.ts

import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';
import { environment } from '../environments/environment';
import { Router } from '@angular/router';


@Injectable({
  providedIn: 'root'
})
export class SocketService {

  private socket!: WebSocket;
  private reconnecting = false;
  token = localStorage.getItem("token");
  router!:Router;


  public messages$ = new Subject<any>();
  baseUrl = `${environment.wsUrl}/ws`

  connect() {
    console.log('inside socket loop');

     if (this.isTokenExpired()) {

    localStorage.removeItem('token');

    this.router.navigate(['/login']);

    return;
  }
    
    this.socket = new WebSocket(`${this.baseUrl}?token=${this.token}`);

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
    console.log('DISCONNECTED');
      this.startReconnect();

    };
  }

  sendQuestion(question: string) {

    if (this.socket.readyState === WebSocket.OPEN) {
    console.log('Socket not connected. Reconnecting...');


      this.socket.send(question);

    } else {

      console.log('Socket not connected');
    }
  }

  private startReconnect() {

  if (this.reconnecting) {
    return;
  }

  this.reconnecting = true;

  const reconnect = () => {

    setTimeout(() => {

      if (this.isTokenExpired()) {

        console.log('JWT expired');

        localStorage.removeItem('token');

        this.socket?.close();

        this.router.navigate(['/login']);

        return;
      }

      if (this.socket?.readyState === WebSocket.OPEN) {
        this.reconnecting = false;
        return;
      }

      console.log('RECONNECTING...');

      this.connect();

      reconnect();

    }, 5000);

  };

  reconnect();
  }

private isTokenExpired(): boolean {

  const token = localStorage.getItem('token');

  if (!token) {
    return true;
  }

  try {

    const payload = JSON.parse(
      atob(token.split('.')[1])
    );
    console.log(payload,'payload');
    
    return payload.exp * 1000 < Date.now();

  } catch {
    return true;
  }
}
}
