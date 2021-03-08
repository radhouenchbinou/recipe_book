import { Component, Input, OnInit } from '@angular/core';
import { shoppingListService } from 'src/app/shoping-list/shopping-list.service';
import { Recipe } from '../recipe.module';
import { RecipeService } from '../recipe.service';

@Component({
  selector: 'app-recipe-detail',
  templateUrl: './recipe-detail.component.html',
  styleUrls: ['./recipe-detail.component.css']
})
export class RecipeDetailComponent implements OnInit {
  @Input() recipe: Recipe;
  
  constructor(private recipeService: RecipeService) { }

  ngOnInit(): void {
  }

  onAddToShopList(){
    this.recipeService.addIngredToShopList(this.recipe.ingredients);
  }

}
