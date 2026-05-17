import { Component, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { SocketService } from '../services/socket.service';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet,FormsModule],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
  protected readonly title = signal('frontend');

    question = '';

  constructor(
    private socketService: SocketService
  ) {}

  ngOnInit(): void {
    this.socketService.connect();
  }

  send() {
    this.socketService.sendQuestion(this.question);
  }
}
