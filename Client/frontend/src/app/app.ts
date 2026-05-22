import { Component, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { SocketService } from '../services/socket.service';
import { FormsModule } from '@angular/forms';
import { Chat} from './chat/chat';
@Component({
  selector: 'app-root',
  imports: [RouterOutlet,FormsModule,Chat],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
}
