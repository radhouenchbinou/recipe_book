import { Component, Input, OnInit } from '@angular/core';
import { Recipe } from '../recipe.module';

@Component({
  selector: 'app-recipe-item',
  templateUrl: './recipe-tem.component.html',
  styleUrls: ['./recipe-tem.component.css']
})
export class RecipeTemComponent implements OnInit {
  @Input() recipe: Recipe;
  @Input() index : number;

  constructor() { }
  ngOnInit(): void {
  }



}
