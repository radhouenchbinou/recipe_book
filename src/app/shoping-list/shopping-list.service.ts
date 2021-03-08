import { EventEmitter } from "@angular/core";
import { Ingerdients } from "../shared/Ingredients.module";

export class shoppingListService {
    ingredientsChanged = new EventEmitter<Ingerdients[]>();
    private ingerdients: Ingerdients[] = [
        new Ingerdients('couscous', 1,'kg'),
        new Ingerdients('viande', 1,'kg'),
        new Ingerdients('pomme de terre', 2,'kg')
    ];

    getIngredients() {
        return this.ingerdients.slice();
    }

    addIngredient(ingredient: Ingerdients){
        this.ingerdients.push(ingredient)
        this.ingredientsChanged.emit(this.ingerdients.slice());
    }

    addIngredients(ingredients : Ingerdients[]){
        //for (let ingredient of ingredients){
          //  this.addIngredient(ingredient);
        //}
        this.ingerdients.push(...ingredients);
        this.ingredientsChanged.emit(this.ingerdients.slice());
    }
}