import { Component, signal } from '@angular/core';
import { SocketService } from '../services/socket.service';
import { FormsModule } from '@angular/forms';
import { Chat} from './chat/chat';
import { Login } from "./login/login";
@Component({
  selector: 'app-root',
  imports: [FormsModule, Chat, Login],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
}
