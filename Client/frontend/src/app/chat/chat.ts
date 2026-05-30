import { Component, NgZone, ChangeDetectorRef } from '@angular/core';
import { SocketService } from '../../services/socket.service';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-chat',
  imports: [FormsModule, CommonModule],
  templateUrl: './chat.html',
  styleUrl: './chat.scss'
})
export class Chat {

  question = '';
  messages: any[] = [];
  loading = false;

  constructor(
    private socketService: SocketService,
    private ngZone: NgZone,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {

    this.socketService.connect();

    this.socketService.messages$.subscribe((data) => {
      console.log('data',data)
      this.ngZone.run(() => {

        this.messages = [
          ...this.messages,
          {
            role: 'assistant',
            content: data.answer,
            followUps:
              typeof data.follow_ups === 'string'
                ? data.follow_ups
                    .split('\n')
                    .map((x: string) => x.trim())
                    .filter((x: string) => x)
                : data.follow_ups || []
          }
        ];

        this.loading = false;

        this.cdr.detectChanges();
      });

    });
  }

  sendMessage(): void {

    if (!this.question.trim()) {
      return;
    }

    this.messages = [
      ...this.messages,
      {
        role: 'user',
        content: this.question
      }
    ];

    this.loading = true;

    this.socketService.sendQuestion(this.question);

    this.question = '';

    this.cdr.detectChanges();
  }

  askFollowUp(question: string): void {
    this.question = question;
    this.sendMessage();
  }
}