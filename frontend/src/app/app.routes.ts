import { Routes } from '@angular/router';
import { LoginRegister } from './login-register/login-register';
import { Home } from './home/home';
import { RegisterAsset } from './register-asset/register-asset';

export const routes: Routes = [
  { path: '', component: LoginRegister },
  { path: 'home', component: Home },
  { path: 'register-asset', component: RegisterAsset }
];
