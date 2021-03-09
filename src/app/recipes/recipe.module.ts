import { Ingerdients } from "../shared/Ingredients.module";

export class Recipe {
    public name: string;
    public description: string;
    public imagePath: string;
    public ingredients: Ingerdients[];
    constructor(name: string, description: string, imagePath: string, ingredients: Ingerdients[]) {

        this.name = name;
        this.description = description;
        this.imagePath = imagePath;
        this.ingredients=ingredients
    }
}