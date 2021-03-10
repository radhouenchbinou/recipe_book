import { AuthService,AuthResponseData } from './auth.service';
import { Component, OnInit } from '@angular/core';
import { NgForm } from '@angular/forms';
import { Router } from '@angular/router';
import { Observable } from 'rxjs';

@Component({
  selector: 'app-auth',
  templateUrl: './auth.component.html',
  styleUrls: ['./auth.component.css']
})
export class AuthComponent implements OnInit {
  isInLogin = true;
  isLoading = false;
  error: string=null;
  constructor(private authService: AuthService, private router: Router) { }

  onSwitchMode() {
    this.isInLogin = !this.isInLogin;
  }

  ngOnInit(): void {
  }


  onSubmit(form: NgForm): void {
    if (!form.valid) { return; }
    console.log(form.value)
    const email = form.value.email;
    const password = form.value.password;
    let authObs: Observable<AuthResponseData>;

    this.isLoading = true;
    if (!this.isInLogin) authObs = this.authService.signUp(email, password)
    else{
      authObs = this.authService.login(email, password);

    }
    authObs.subscribe(
      resData => {
        console.log("thats resdata = " +resData);
        this.router.navigate(['./recipes']);
      },
      errorMessage => {
        this.error = errorMessage;
        console.log(errorMessage);
        this.isLoading = false;
        
      }
    )
    form.reset();
  }

}
