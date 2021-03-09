import { HttpClient } from "@angular/common/http";
import { Injectable } from "@angular/core";
import { Recipe } from "../recipes/recipe.module";
import { RecipeService } from "../recipes/recipe.service";
import {map, tap} from "rxjs/operators"
const FIREBASE_URL ='https://tunisianfood-3587a-default-rtdb.firebaseio.com';

@Injectable()
export class DataStorageService {
    constructor(private httpclient: HttpClient, private recipeService: RecipeService) {};

    saveRecipes(){
        const recipes = this.recipeService.getRecipes();
         this.httpclient.put(FIREBASE_URL+ '/recipes.json', recipes).subscribe(
             response => {
                 console.log(response);
             }
         );
    }

    fetchRecipes(){
        this.httpclient.get(FIREBASE_URL + '/recipes.json').subscribe(
            recipes => {
                let recipeList = <Recipe[]>recipes;
                recipeList.map(recipe =>{
                    recipe.ingredients = recipe.ingredients? recipe.ingredients : [];
                })
                
                console.log(recipes);
                this.recipeService.setRecipes(recipeList);
            }
        );
    }

}