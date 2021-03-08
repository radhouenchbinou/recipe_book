import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Params } from '@angular/router';
import { Recipe } from '../recipe.module';
import { RecipeService } from '../recipe.service';

@Component({
  selector: 'app-recipe-detail',
  templateUrl: './recipe-detail.component.html',
  styleUrls: ['./recipe-detail.component.css']
})
export class RecipeDetailComponent implements OnInit {
  recipe: Recipe;
  id: number;
  
  constructor(private recipeService: RecipeService, 
              private actiave: ActivatedRoute) { }

  ngOnInit(): void {
    this.actiave.params.subscribe(
      (params: Params) => {
          this.id = +params['id'];
          this.recipe= this.recipeService.getRecipe(this.id);
      }
    );
  }

  onAddToShopList(){
    this.recipeService.addIngredToShopList(this.recipe.ingredients);
  }

}
