import { Component, OnInit } from '@angular/core';
import { Subscription } from 'rxjs';
import { Ingerdients } from '../shared/Ingredients.module';
import { shoppingListService } from './shopping-list.service';

@Component({
  selector: 'app-shoping-list',
  templateUrl: './shoping-list.component.html',
  styleUrls: ['./shoping-list.component.css'],
})
export class ShopingListComponent implements OnInit {
  ingerdients: Ingerdients[];
  private igChangeSubs: Subscription;
  constructor(private shoppingListService: shoppingListService) { }

  ngOnInit(): void {
    this.ingerdients = this.shoppingListService.getIngredients();
    this.igChangeSubs = this.shoppingListService.ingredientsChanged.subscribe(
      (ingredients: Ingerdients[]) => {
        this.ingerdients = ingredients
      }
    )
  }

  ngOnDestroy(): void {
    //Called once, before the instance is destroyed.
    //Add 'implements OnDestroy' to the class.
    this.igChangeSubs.unsubscribe();
  }

}
