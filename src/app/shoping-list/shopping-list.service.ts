import { THIS_EXPR } from "@angular/compiler/src/output/output_ast";
import { EventEmitter } from "@angular/core";
import { Subject } from 'rxjs';

import { Ingerdients } from "../shared/Ingredients.module";

export class shoppingListService {
    ingredientsChanged = new Subject<Ingerdients[]>();
    startedEditing = new Subject<number>();
    private ingerdients: Ingerdients[] = [
        new Ingerdients('couscous', 1, 'kg'),
        new Ingerdients('meat', 1, 'kg'),
        new Ingerdients('potato', 2, 'kg')
    ];

    clearIngredients(){
        this.ingerdients = [];
        this.ingredientsChanged.next(this.ingerdients.slice())
    }

    deleteIngredient(index: number){
        this.ingerdients.splice(index,1);
        this.ingredientsChanged.next(this.ingerdients.slice());
    }

    getIngredient(index: number) {
        return this.ingerdients[index];
    }

    updateIngredient(index: number, newIng: Ingerdients){
        this.ingerdients[index]=newIng;
        this.ingredientsChanged.next(this.ingerdients.slice());
    }

    getIngredients() {
        return this.ingerdients.slice();
    }

    addIngredient(ingredient: Ingerdients) {
        this.ingerdients.push(ingredient)
        this.ingredientsChanged.next(this.ingerdients.slice());
    }

    addIngredients(ingredients: Ingerdients[]) {
        //for (let ingredient of ingredients){
        //  this.addIngredient(ingredient);
        //}
        this.ingerdients.push(...ingredients);
        this.ingredientsChanged.next(this.ingerdients.slice());
    }
}