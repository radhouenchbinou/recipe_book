export class Recipe {
    public name: String;
    public description: string;
    public imagePath: string;

    constructor(name: string, description: string, imagePath: string) {

        this.name = name;
        this.description = description;
        this.imagePath = imagePath;

    }
}