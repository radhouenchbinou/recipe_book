import { EventEmitter, Injectable } from "@angular/core";
import { Subject } from "rxjs";
import { Ingerdients } from "../shared/Ingredients.module";
import { shoppingListService } from "../shoping-list/shopping-list.service";
import { Recipe } from "./recipe.module";

@Injectable()
export class RecipeService {

    private recipes: Recipe[] = [
        new Recipe('CousCous','couscous tunisien',
        'https://upload.wikimedia.org/wikipedia/commons/b/b4/Tunisian_couscous.jpg',[
            new Ingerdients('couscous', 1,'kg'),
            new Ingerdients('meat', 1,'kg'),
            new Ingerdients('potato', 1,'kg'),
            new Ingerdients('onion', 2,'kg'),
        ]),
        new Recipe("kanoumenya","kamouneya tounseya",
         "https://i.pinimg.com/originals/fd/2e/e5/fd2ee582870a2315d775841bd708fa69.jpg",
         [
            new Ingerdients('liver', 1,'kg'),
            new Ingerdients('meat', 1,'kg'),
            new Ingerdients('cumin', 2,'cafee\'s spoon'),
             
         ])
    ];

    getRecipes(){
        return this.recipes.slice();
    }

    constructor(private shopListService: shoppingListService){

    }

    getRecipe(id: number){
        return this.recipes.slice()[id];
    }

    addIngredToShopList(ingredients: Ingerdients[]){
        this.shopListService.addIngredients(ingredients);
    }


}