import { Component, Input, OnInit, EventEmitter, Output } from '@angular/core';
import { Recipe } from '../recipe.module';

@Component({
  selector: 'app-recipe-item',
  templateUrl: './recipe-tem.component.html',
  styleUrls: ['./recipe-tem.component.css']
})
export class RecipeTemComponent implements OnInit {
  @Input() recipe: Recipe;
  @Output() recipeSelected = new EventEmitter<void>();

  constructor() { }

  ngOnInit(): void {
  }

  onSelected() {
    this.recipeSelected.emit();
  }
}
