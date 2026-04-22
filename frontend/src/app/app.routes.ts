import { Routes } from '@angular/router';
import { LoginRegister } from './login-register/login-register';
import { Home } from './home/home';
import { RegisterAsset } from './register-asset/register-asset';
import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  { path: '', component: LoginRegister },
  { path: 'home', component: Home, canActivate: [authGuard] },
  { path: 'register-asset', component: RegisterAsset, canActivate: [authGuard] }
];
