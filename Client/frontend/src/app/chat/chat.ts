import { Component } from '@angular/core';
import { SocketService } from '../../services/socket.service';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-chat',
  imports: [FormsModule,CommonModule],
  templateUrl: './chat.html',
  styleUrl: './chat.scss',
})
export class Chat {
    question = '';

  messages: any[] = [];

  loading = false;

  constructor(private socketService: SocketService) {}

  ngOnInit(): void {


    this.socketService.connect();

    this.socketService.messages$.subscribe((data) => {

      this.loading = false;

      this.messages.push({
        role: 'assistant',
        content: data.answer,
        followUps: data.follow_ups || []
      });
    });
  }

  sendMessage() {

    if (!this.question.trim()) return;

    this.messages.push({
      role: 'user',
      content: this.question
    });

    this.loading = true;

    this.socketService.sendQuestion(this.question);

    this.question = '';
  }

  askFollowUp(question: string) {

    this.question = question;

    this.sendMessage();
  }
}
