import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import { Recipe } from '../recipe.module';

@Component({
  selector: 'app-recipe-list',
  templateUrl: './recipe-list.component.html',
  styleUrls: ['./recipe-list.component.css']
})
export class RecipeListComponent implements OnInit {
  @Output() recipeWasSelected = new EventEmitter<Recipe>();
  recipes: Recipe[] = [
    new Recipe('CousCous','couscous tunisien','https://upload.wikimedia.org/wikipedia/commons/b/b4/Tunisian_couscous.jpg'),
    new Recipe("kanoumenya","kamouneya tounseya", "https://i.pinimg.com/originals/fd/2e/e5/fd2ee582870a2315d775841bd708fa69.jpg")
  ];
  constructor() { }

  ngOnInit(): void {
  }

  onRecipeSelected(recipe: Recipe){
    this.recipeWasSelected.emit(recipe);
  }

}
