import { Component, Input, OnInit } from '@angular/core';
import { Recipe } from '../recipe.module';
import { RecipeService } from '../recipe.service';

@Component({
  selector: 'app-recipe-item',
  templateUrl: './recipe-tem.component.html',
  styleUrls: ['./recipe-tem.component.css']
})
export class RecipeTemComponent implements OnInit {
  @Input() recipe: Recipe;

  constructor(private recipeService : RecipeService) { }

  ngOnInit(): void {
  }

  onSelected() {
    this.recipeService.recipeSelected.emit(this.recipe);
  }
}
