import { Component, OnInit, EventEmitter, Output } from '@angular/core';
import { Subscription } from 'rxjs';
import { AuthService } from '../auth/auth/auth.service';
import { DataStorageService } from '../shared/data-storage.service';


@Component({
  selector: 'app-header',
  templateUrl: './header.component.html',
  styleUrls: ['./header.component.css']
})
export class HeaderComponent implements OnInit {
  isAuthenticated = false;
  private userSubscription: Subscription;

  constructor(private dataStorageService : DataStorageService, private authService : AuthService) { }

  ngOnInit(): void {
    this.userSubscription= this.authService.user.subscribe(
      user => {
        this.isAuthenticated = !!user;
        console.log(!user);
        console.log(!!user);
      }
    );
    
  }

  onSaveData(){
    this.dataStorageService.saveRecipes();
  }

  onFetchData(){
    console.log('onheaderfetchData')
    this.dataStorageService.fetchRecipes().subscribe();
    console.log("endHeaderFetchData")
  }

  ngOnDestroy(): void {
    //Called once, before the instance is destroyed.
    //Add 'implements OnDestroy' to the class.
    this.userSubscription.unsubscribe();
  }
  

}
