import { Component, OnInit } from '@angular/core';
import { AuthService } from './auth/auth/auth.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit{
  title = 'tunisian food recipe book';
  loadedFeature = 'recipe';
  constructor(private authService: AuthService){}
  
  ngOnInit(): void {
    console.log('on init app')
    this.authService.autoLogin();  
  }

}
