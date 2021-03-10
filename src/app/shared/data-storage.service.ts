import { HttpClient, HttpParams } from "@angular/common/http";
import { Injectable } from "@angular/core";
import { Recipe } from "../recipes/recipe.module";
import { RecipeService } from "../recipes/recipe.service";
import { exhaustMap, map, take, tap } from "rxjs/operators"
import { AuthService } from "../auth/auth/auth.service";

const FIREBASE_URL = 'https://tunisianfood-3587a-default-rtdb.firebaseio.com';

@Injectable()
export class DataStorageService {
    constructor(private httpclient: HttpClient, private recipeService: RecipeService, private authService: AuthService) { };

    saveRecipes() {
        const recipes = this.recipeService.getRecipes();
        this.httpclient.put(FIREBASE_URL + '/recipes.json', recipes).subscribe(
            response => {
                console.log(response);
            }
        );
    }

    fetchRecipes() {
        console.log('fromfetchData')
        return this.httpclient.get(FIREBASE_URL + '/recipes.json',
        ).pipe(
            map(recipes => {
                console.log('infetchDataFromMap')
                return (<Recipe[]>recipes).map(recipe => {
                    return {
                        ...recipe, ingredients: recipe.ingredients ? recipe.ingredients : []
                    };
                }
                );
            }),
            tap(recipes => {
                this.recipeService.setRecipes(recipes);

            })
        )
    }
}