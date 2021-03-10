import { Injectable } from "@angular/core";
import { ActivatedRouteSnapshot, CanActivate, Router, RouterStateSnapshot, UrlTree } from "@angular/router";
import { Observable } from "rxjs";
import { map, take } from "rxjs/operators";

import { AuthService } from "./auth.service";

@Injectable({providedIn: 'root'})
export class AuthGuard implements CanActivate{
 
    constructor(private authService: AuthService, private router: Router){}

    canActivate(
        route: ActivatedRouteSnapshot,
         router: RouterStateSnapshot): boolean | Promise<boolean> | Observable<boolean | UrlTree > {
            return this.authService.user.pipe(
                take(1),
                map(user =>{
                   const isAuth = !!user;
                   return isAuth? true : this.router.createUrlTree(['/auth']) 
                })
            );
         }

}