import { HttpClient, HttpErrorResponse } from "@angular/common/http";
import { Injectable } from "@angular/core";
import { Router } from "@angular/router";
import { BehaviorSubject, Subject, throwError } from "rxjs";
import { catchError, tap } from "rxjs/operators";

import { User } from "./user.module";
const WEB_API_KEY = "AIzaSyCE18KdLoxCQCXzg5oapP_Msnn21PAHFq4";
const FIREBASE_SIGNUP_URL = "https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=" + WEB_API_KEY;
const FIREBASE_LOGIN_URL = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=" + WEB_API_KEY;
export interface AuthResponseData {
    kind: string;
    idToken: string;
    email: string;
    refreshToken: string;
    expiresIn: string;
    localId: string;
    registered?: boolean;
}


@Injectable({ providedIn: 'root' })
export class AuthService {
    user = new BehaviorSubject<User>(null);
    private tokenValidationTimer : any;

    constructor(private http: HttpClient, private router: Router) { }

    login(email: string, password: string) {
        return this.http.post<AuthResponseData>(FIREBASE_LOGIN_URL, {
            email: email,
            password: password,
            returnSecureToken: true

        }).pipe(
            catchError(this.handleError),
            tap(
                resData => {
                    this.handleAuthentication(resData.email, resData.localId, resData.idToken, +resData.expiresIn)
                }
            )
        )
    }

    logout() {
        this.user.next(null);
        localStorage.removeItem('user');
        if(this.tokenValidationTimer) clearTimeout(this.tokenValidationTimer)
        this.router.navigate(['/auth'])

    }

    autoLogout(expirationDuration: number) {
        this.tokenValidationTimer= setTimeout(() => {
            this.logout();
        },expirationDuration)
    }

    autoLogin() {
        const userData: {
            email: string,
            id: string,
            _token: string,
            _tokenExpirationDate: string,
        } = JSON.parse(localStorage.getItem('user'));
        if (!userData) {
            return;
        }
        const newLoadedUser = new User(
            userData.email,
            userData.id,
            userData._token,
            new Date(userData._tokenExpirationDate));

        if (newLoadedUser.token) {
            this.user.next(newLoadedUser)
            const expirationDuration =  new Date(userData._tokenExpirationDate).getTime() - new Date().getTime(); 
            this.autoLogout(expirationDuration)
        };
    }


    signUp(email: string, password: string) {
        return this.http.post<AuthResponseData>(FIREBASE_SIGNUP_URL, {
            email: email,
            password: password,
            returnSecureToken: true
        }).pipe(
            catchError(this.handleError),
            tap(
                resData => {
                    this.handleAuthentication(resData.email, resData.localId, resData.idToken, +resData.expiresIn)
                }
            )
        );
    }


    private handleAuthentication(email: string, userId: string, token: string, expiresIn: number) {
        const expirationDate = new Date(new Date().getTime() + expiresIn * 1000)
        const newUser = new User(
            email,
            userId,
            token,
            expirationDate);
        console.log(newUser)
        this.user.next(newUser);
        this.autoLogout(expiresIn * 1000)
        localStorage.setItem('user', JSON.stringify(newUser));
    }

    private handleError(errorRes: HttpErrorResponse) {
        let errorMessage = 'an unknown error occurred'
        if (!errorRes.error || !errorRes.error.error) {
            return throwError(errorMessage)
        }
        switch (errorRes.error.error.message) {
            case 'EMAIL_NOT_FOUND': {
                errorMessage = 'no account with this email address';
                break;
            }
            case 'INVALID_PASSWORD': {
                errorMessage = 'Password is incorrect';
                break;
            }
            case 'USER_DISABLED': {
                errorMessage = 'this user is disabled';
                break;
            };
            case 'EMAIL_EXISTS': {
                errorMessage = 'Email already exists';
                break;
            }
            case 'OPERATION_NOT_ALLOWED': {
                errorMessage = 'Operation not allowedoperation is not allowed';
                break;
            }
            case 'TOO_MANY_ATTEMPTS_TRY_LATER': {
                errorMessage = 'too many attempts please try again later'
                break;
            };
        }
        return throwError(errorMessage)
    }
}