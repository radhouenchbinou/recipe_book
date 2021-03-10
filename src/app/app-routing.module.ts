import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AuthComponent } from './auth/auth/auth.component';
import { AuthGuard } from './auth/auth/auth.guard';
import { RecipeDetailComponent } from './recipes/recipe-detail/recipe-detail.component';
import { RecipeEditComponent } from './recipes/recipe-edit/recipe-edit.component';
import { RecipesResolverSercice } from './recipes/recipe-resolver.service';
import { RecipesStartComponent } from './recipes/recipes-start/recipes-start.component';
import { RecipesComponent } from './recipes/recipes.component';
import { ShopingListComponent } from './shoping-list/shoping-list.component';

const routes: Routes = [
  {path:'',redirectTo:'/recipes', pathMatch:'full'},
  {path: 'recipes', component: RecipesComponent,
  canActivate: [AuthGuard] 
  ,children: [
    {path:'',component:RecipesStartComponent},
    {path: 'new', component: RecipeEditComponent,resolve: [RecipesResolverSercice]},
    {path:':id', component:RecipeDetailComponent,resolve: [RecipesResolverSercice]},
    {path: ':id/edit', component: RecipeEditComponent}
  ],resolve: [RecipesResolverSercice]},
  {path: 'shopping-list', component: ShopingListComponent},
  {path: 'auth', component: AuthComponent}
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
