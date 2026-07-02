import { Component, NgZone, ChangeDetectorRef } from '@angular/core';
import { SocketService } from '../../services/socket.service';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';

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
  stageText = '';
  stageVisible = false;
  isLimitReached: boolean = false;
  errorMessage = '';

  constructor(
    private socketService: SocketService,
    private ngZone: NgZone,
    private cdr: ChangeDetectorRef,
    private router: Router
  ) { }

  ngOnInit(): void {
    this.socketService.connect();

    this.socketService.messages$.subscribe((data) => {
      console.log('data', data);

      if (data?.type === 'error') {
  this.errorMessage = data.message || 'Request limit reached.';
  this.isLimitReached = true;
  this.loading = false;
  this.stageVisible = false;
  this.cdr.detectChanges();
  return;
}
      this.ngZone.run(() => {
        const parseFollowUps = (followUps: any) => {
          if (Array.isArray(followUps)) {
            return followUps;
          }
          if (typeof followUps === 'string') {
            return followUps
              .split('\n')
              .map((x: string) => x.trim())
              .filter((x: string) => x);
          }
          return [];
        };

        const stageIndex = this.messages.findIndex(
          (msg) => msg.role === 'assistant' && msg.stage === true
        );
        const streamingIndex = this.messages.findIndex(
          (msg) => msg.role === 'assistant' && msg.streaming === true
        );

        if (data?.type === 'stage') {
          this.stageText = data.message || '';
          this.stageVisible = true;
        } else if (data?.type === 'token') {
          const deltaText = data.value || '';

          if (streamingIndex >= 0) {
            this.messages[streamingIndex] = {
              ...this.messages[streamingIndex],
              content: (this.messages[streamingIndex].content || '') + deltaText
            };
          } else {
            this.messages = [
              ...this.messages,
              {
                role: 'assistant',
                content: deltaText,
                followUps: [],
                stage: false,
                streaming: true
              }
            ];
          }
        } else if (data?.type === 'final') {
          const answer = data.answer || '';
          const followUps = parseFollowUps(data.follow_ups);

          this.stageVisible = false;
          const finalStreamingIndex = this.messages.findIndex(
            (msg) => msg.role === 'assistant' && msg.streaming === true
          );

          if (finalStreamingIndex >= 0) {
            this.messages[finalStreamingIndex] = {
              ...this.messages[finalStreamingIndex],
              followUps,
              type: 'final',
              streaming: false
            };
          } else {
            this.messages = [
              ...this.messages,
              {
                role: 'assistant',
                content: answer,
                followUps,
                type: 'final',
                streaming: false
              }
            ];
          }

          this.loading = false;
        } else {
          const followUps = parseFollowUps(data?.follow_ups);
          const answer = data?.answer || '';

          this.messages = [
            ...this.messages,
            {
              role: 'assistant',
              content: answer,
              followUps,
              type: 'final',
              stage: false,
              streaming: false
            }
          ];

          this.stageVisible = false;
          this.loading = false;
        }

        this.cdr.detectChanges();
      });
    });
  }

  goToLogin(): void {
  localStorage.removeItem('token'); // optional, if you store JWT in localStorage
  this.router.navigate(['/login']);
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

    this.stageVisible = false;
    this.stageText = '';

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