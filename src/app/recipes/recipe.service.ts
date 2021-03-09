import { EventEmitter, Injectable } from "@angular/core";
import { Subject } from "rxjs";
import { Ingerdients } from "../shared/Ingredients.module";
import { shoppingListService } from "../shoping-list/shopping-list.service";
import { Recipe } from "./recipe.module";

@Injectable()
export class RecipeService {
    recipesChanged = new Subject<Recipe[]>();

    private recipes: Recipe[] = [];

    getRecipes() {
        return this.recipes.slice();
    }

    constructor(private shopListService: shoppingListService) {}

    setRecipes(recipes : Recipe[]){
        this.recipes = recipes
        this.recipesChanged.next(this.recipes.slice());
    }
    

    getRecipe(id: number) {
        return this.recipes.slice()[id];
    }

    addIngredToShopList(ingredients: Ingerdients[]) {
        this.shopListService.addIngredients(ingredients);
    }

    addRecipe(recipe: Recipe) {
        this.recipes.push(recipe);
        this.recipesChanged.next(this.recipes.slice())
    }

    updateRecipe(index: number, recipe: Recipe) {
        this.recipes[index] = recipe;
        this.recipesChanged.next(this.recipes.slice())

    }

    deleteRecipe(index: number) {
        this.recipes.splice(index,1)
        this.recipesChanged.next(this.recipes.slice());
    }


}