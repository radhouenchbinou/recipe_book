import { Component, OnInit } from '@angular/core';
import { ingerdients } from '../shared/Ingredients.module';

@Component({
  selector: 'app-shoping-list',
  templateUrl: './shoping-list.component.html',
  styleUrls: ['./shoping-list.component.css']
})
export class ShopingListComponent implements OnInit {
  ingerdients: ingerdients[] = [
    new ingerdients('couscous', 1),
    new ingerdients('viande', 1),
    new ingerdients('pomme de terre', 2)
  ];

  constructor() { }

  ngOnInit(): void {
  }

  onIngredientAdded(ing: ingerdients) {
    this.ingerdients.push(ing);
  }

}
