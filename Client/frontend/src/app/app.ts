import { Component, signal } from '@angular/core';
import { SocketService } from '../services/socket.service';
import { FormsModule } from '@angular/forms';
import { Chat} from './chat/chat';
@Component({
  selector: 'app-root',
  imports: [FormsModule,Chat],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
}
