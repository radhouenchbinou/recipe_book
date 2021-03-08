import { Component, OnInit, ViewChild, } from '@angular/core';
import { NgForm } from '@angular/forms';
import { Subscription } from 'rxjs';
import { Ingerdients } from 'src/app/shared/Ingredients.module';
import { shoppingListService } from '../shopping-list.service';

@Component({
  selector: 'app-shopping-edit',
  templateUrl: './shopping-edit.component.html',
  styleUrls: ['./shopping-edit.component.css']
})
export class ShoppingEditComponent implements OnInit {
  @ViewChild('f') slForm: NgForm;
  subscription: Subscription;
  editMode = false;
  editedItemIndex: number;
  editedItem: Ingerdients

  constructor(private shoppingListService: shoppingListService) { }

  ngOnInit(): void {
    this.subscription = this.shoppingListService.startedEditing.subscribe(
      (index: number) => {
        this.editedItemIndex = index;
        this.editMode = true;
        this.editedItem = this.shoppingListService.getIngredient(index)
        this.slForm.setValue({
          name: this.editedItem.name,
          amount: this.editedItem.amount,
          unity: this.editedItem.unity
        })
      }
    );
  }

  onClear(form: NgForm) {
    this.shoppingListService.clearIngredients();
    this.editMode=false;
    form.reset();
  }

  onDelete(form: NgForm) {
    this.shoppingListService.deleteIngredient(this.editedItemIndex);
    this.editMode=false;
    form.reset();
  }

  onSubmit(form: NgForm) {
    const value = form.value;
    const newIngredient = new Ingerdients(value.name, value.amount, value.unity);
    console.log(value)
    if (this.editMode) {
      this.shoppingListService.updateIngredient(this.editedItemIndex, newIngredient);

    }
    else {
      this.shoppingListService.addIngredient(newIngredient);
    };
    this.editMode = false;
    form.reset()
  }

  ngOnDestroy(): void {
    //Called once, before the instance is destroyed.
    //Add 'implements OnDestroy' to the class.
    this.subscription.unsubscribe();
  }

}
