import { Component, ElementRef, EventEmitter, OnInit, Output, ViewChild } from '@angular/core';
import { Ingerdients } from 'src/app/shared/Ingredients.module';
import { shoppingListService } from '../shopping-list.service';

@Component({
  selector: 'app-shopping-edit',
  templateUrl: './shopping-edit.component.html',
  styleUrls: ['./shopping-edit.component.css']
})
export class ShoppingEditComponent implements OnInit {

  @ViewChild('nameInput') nameInputRef: ElementRef;
  @ViewChild('amountInput') amountInputRef: ElementRef;
  @ViewChild('unityInput') unityInputRef: ElementRef;


  @Output() ingredientAdded = new EventEmitter<Ingerdients>()

  constructor(private shoppingListService: shoppingListService) { }

  ngOnInit(): void {
  }

  onAddItem() {
    const ingName = this.nameInputRef.nativeElement.value;
    const ingAmount = this.amountInputRef.nativeElement.value;
    const ingunity = this.unityInputRef.nativeElement.value;
    const newIngredient = new Ingerdients(ingName,ingAmount,ingunity);
    this.shoppingListService.addIngredient(newIngredient);
  }

}
