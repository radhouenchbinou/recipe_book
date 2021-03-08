import { Component, OnInit } from '@angular/core';
import { Ingerdients } from '../shared/Ingredients.module';
import { shoppingListService } from './shopping-list.service';

@Component({
  selector: 'app-shoping-list',
  templateUrl: './shoping-list.component.html',
  styleUrls: ['./shoping-list.component.css'],
})
export class ShopingListComponent implements OnInit {
  ingerdients :Ingerdients[];

  constructor(private shoppingListService: shoppingListService) { }

  ngOnInit(): void {
    this.ingerdients= this.shoppingListService.getIngredients();
    this.shoppingListService.ingredientsChanged.subscribe(
      (ingredients : Ingerdients[]) => {
        this.ingerdients=ingredients
      }
    )
  } 

}
