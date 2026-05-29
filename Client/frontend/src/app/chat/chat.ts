import { ChangeDetectorRef, Component } from '@angular/core';
import { SocketService } from '../../services/socket.service';
import { FormsModule } from '@angular/forms';
import { CommonModule, NgIf } from '@angular/common';

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

  constructor(private socketService: SocketService,
      private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {


    this.socketService.connect();

this.socketService.messages$.subscribe((data) => {
  console.log(data,'data');
  


  this.messages.push({
    role: 'assistant',
    content: data.answer,
   followUps: typeof data.follow_ups === 'string'
  ? data.follow_ups
      .split('\n')
      .map((x: string) => x.trim())
      .filter((x: string) => x)
  : data.follow_ups || []
  });

});
  this.loading = false;

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
